package tests

import (
	"bytes"
	"encoding/json"
	"net/http"
	"os"
	"strings"
	"testing"
)

var (
	searchEndpoints = []string{"/searching", "/api/searching"}
	indexEndpoints  = []string{"/indexing", "/api/indexing"}
)

type healthResponse struct {
	Status  string `json:"status"`
	Service string `json:"service"`
}

type apiErrorEnvelope struct {
	Error struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

func baseURL() string {
	if value := strings.TrimSpace(os.Getenv("RAG_API_BASE_URL")); value != "" {
		return strings.TrimRight(value, "/")
	}
	return "http://localhost:5001"
}

func doRequest(t *testing.T, method, path string, body []byte, contentType string) *http.Response {
	t.Helper()

	url := baseURL() + path
	req, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		t.Fatalf("new request %s %s: %v", method, url, err)
	}

	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request %s %s failed: %v", method, url, err)
	}
	return resp
}

func decodeJSON[T any](t *testing.T, response *http.Response, out *T) {
	t.Helper()
	defer response.Body.Close()
	if err := json.NewDecoder(response.Body).Decode(out); err != nil {
		t.Fatalf("decode JSON failed: %v", err)
	}
}

func assertErrorCode(t *testing.T, response *http.Response, expectedStatus int, expectedCode string) {
	t.Helper()
	if response.StatusCode != expectedStatus {
		defer response.Body.Close()
		t.Fatalf("unexpected status: got %d, want %d", response.StatusCode, expectedStatus)
	}

	var payload apiErrorEnvelope
	decodeJSON(t, response, &payload)

	if payload.Error.Code != expectedCode {
		t.Fatalf("unexpected error code: got %q, want %q", payload.Error.Code, expectedCode)
	}
}

func TestHealthEndpoint(t *testing.T) {
	response := doRequest(t, http.MethodGet, "/", nil, "")
	if response.StatusCode != http.StatusOK {
		defer response.Body.Close()
		t.Fatalf("unexpected status: got %d, want %d", response.StatusCode, http.StatusOK)
	}

	var payload healthResponse
	decodeJSON(t, response, &payload)

	if payload.Status != "ok" {
		t.Fatalf("unexpected status field: got %q", payload.Status)
	}
}

func TestSearchRejectsNonJSONContentType(t *testing.T) {
	for _, endpoint := range searchEndpoints {
		response := doRequest(t, http.MethodPost, endpoint, []byte(`{"query":"hello"}`), "text/plain")
		assertErrorCode(t, response, http.StatusUnsupportedMediaType, "invalid_content_type")
	}
}

func TestSearchRejectsInvalidJSON(t *testing.T) {
	for _, endpoint := range searchEndpoints {
		response := doRequest(t, http.MethodPost, endpoint, []byte(`{"query":`), "application/json")
		assertErrorCode(t, response, http.StatusBadRequest, "invalid_json")
	}
}

func TestSearchRequiresQuery(t *testing.T) {
	for _, endpoint := range searchEndpoints {
		response := doRequest(t, http.MethodPost, endpoint, []byte(`{"top_k":3}`), "application/json")
		if response.StatusCode != http.StatusBadRequest {
			defer response.Body.Close()
			t.Fatalf("unexpected status: got %d, want %d", response.StatusCode, http.StatusBadRequest)
		}

		var payload apiErrorEnvelope
		decodeJSON(t, response, &payload)
		if payload.Error.Message != "Query is required" {
			t.Fatalf("unexpected message: got %q", payload.Error.Message)
		}
	}
}

func TestSearchValidatesTopKRange(t *testing.T) {
	for _, endpoint := range searchEndpoints {
		response := doRequest(t, http.MethodPost, endpoint, []byte(`{"query":"hello","top_k":0}`), "application/json")
		assertErrorCode(t, response, http.StatusBadRequest, "invalid_field")
	}
}

func TestSearchValidatesKeywordsType(t *testing.T) {
	for _, endpoint := range searchEndpoints {
		response := doRequest(t, http.MethodPost, endpoint, []byte(`{"query":"hello","keywords":"tag"}`), "application/json")
		assertErrorCode(t, response, http.StatusBadRequest, "invalid_field")
	}
}

func TestSearchAcceptsVendorJSONContentType(t *testing.T) {
	for _, endpoint := range searchEndpoints {
		response := doRequest(t, http.MethodPost, endpoint, []byte(`{"query":"hello","top_k":1}`), "application/merge-patch+json")
		if response.StatusCode == http.StatusUnsupportedMediaType {
			defer response.Body.Close()
			t.Fatalf("endpoint %s rejected +json media type", endpoint)
		}
		response.Body.Close()
	}
}

func TestIndexingRequiresDocumentName(t *testing.T) {
	for _, endpoint := range indexEndpoints {
		response := doRequest(
			t,
			http.MethodPost,
			endpoint,
			[]byte(`{"documents":[{"content":"x"}]}`),
			"application/json",
		)
		if response.StatusCode != http.StatusBadRequest {
			defer response.Body.Close()
			t.Fatalf("unexpected status: got %d, want %d", response.StatusCode, http.StatusBadRequest)
		}

		var payload apiErrorEnvelope
		decodeJSON(t, response, &payload)
		if payload.Error.Message != "No document name provided" {
			t.Fatalf("unexpected message: got %q", payload.Error.Message)
		}
	}
}

func TestIndexingRequiresDocuments(t *testing.T) {
	for _, endpoint := range indexEndpoints {
		response := doRequest(
			t,
			http.MethodPost,
			endpoint,
			[]byte(`{"document_name":"doc","documents":[]}`),
			"application/json",
		)
		if response.StatusCode != http.StatusBadRequest {
			defer response.Body.Close()
			t.Fatalf("unexpected status: got %d, want %d", response.StatusCode, http.StatusBadRequest)
		}

		var payload apiErrorEnvelope
		decodeJSON(t, response, &payload)
		if payload.Error.Message != "No documents to index" {
			t.Fatalf("unexpected message: got %q", payload.Error.Message)
		}
	}
}

func TestIndexingValidatesDocumentContent(t *testing.T) {
	for _, endpoint := range indexEndpoints {
		response := doRequest(
			t,
			http.MethodPost,
			endpoint,
			[]byte(`{"document_name":"doc","documents":[{"content":"   "} ]}`),
			"application/json",
		)
		assertErrorCode(t, response, http.StatusBadRequest, "invalid_field")
	}
}

func TestSearchAndIndexAliasesBehaveSameForInvalidPayload(t *testing.T) {
	responseA := doRequest(t, http.MethodPost, "/searching", []byte(`{"top_k":3}`), "application/json")
	responseB := doRequest(t, http.MethodPost, "/api/searching", []byte(`{"top_k":3}`), "application/json")

	if responseA.StatusCode != responseB.StatusCode {
		defer responseA.Body.Close()
		defer responseB.Body.Close()
		t.Fatalf("alias status mismatch: /searching=%d /api/searching=%d", responseA.StatusCode, responseB.StatusCode)
	}

	var payloadA apiErrorEnvelope
	var payloadB apiErrorEnvelope
	decodeJSON(t, responseA, &payloadA)
	decodeJSON(t, responseB, &payloadB)
	if payloadA.Error.Code != payloadB.Error.Code {
		t.Fatalf("alias code mismatch: /searching=%s /api/searching=%s", payloadA.Error.Code, payloadB.Error.Code)
	}
}

func TestOptionalIndexAndSearchFlow(t *testing.T) {
	if os.Getenv("RAG_RUN_SLOW_E2E") != "1" {
		t.Skip("set RAG_RUN_SLOW_E2E=1 to run slow E2E scenario with vectorization")
	}

	documentName := "go-e2e-doc"
	indexPayload := `{
	  "document_name":"` + documentName + `",
	  "documents":[{"content":"Гарри Поттер в очках","keywords":["гарри","поттер"]}]
	}`

	indexResponse := doRequest(t, http.MethodPost, "/api/indexing", []byte(indexPayload), "application/json")
	if indexResponse.StatusCode != http.StatusOK {
		defer indexResponse.Body.Close()
		t.Fatalf("indexing failed with status %d", indexResponse.StatusCode)
	}
	indexResponse.Body.Close()

	searchResponse := doRequest(
		t,
		http.MethodPost,
		"/api/searching",
		[]byte(`{"query":"гарри","top_k":3}`),
		"application/json",
	)
	if searchResponse.StatusCode != http.StatusOK {
		defer searchResponse.Body.Close()
		t.Fatalf("search failed with status %d", searchResponse.StatusCode)
	}

	var payload map[string]any
	decodeJSON(t, searchResponse, &payload)
	if _, ok := payload["results"]; !ok {
		t.Fatalf("search response has no 'results': %v", payload)
	}
	if _, ok := payload["total"]; !ok {
		t.Fatalf("search response has no 'total': %v", payload)
	}
}
