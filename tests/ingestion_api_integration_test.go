package tests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"mime/multipart"
	"net/http"
	"strings"
	"testing"
)

type documentUploadResponse struct {
	DocumentID string `json:"document_id"`
	FileName   string `json:"file_name"`
	Status     string `json:"status"`
}

type documentListResponse struct {
	Documents []struct {
		DocumentID string `json:"document_id"`
		FileName   string `json:"file_name"`
	} `json:"documents"`
}

type documentIndexResponse struct {
	JobID      string `json:"job_id"`
	Status     string `json:"status"`
	DocumentID string `json:"document_id"`
}

type jobStatusResponse struct {
	JobID      string `json:"job_id"`
	DocumentID string `json:"document_id"`
	Status     string `json:"status"`
	Progress   int    `json:"progress"`
}

type jobListResponse struct {
	Jobs []jobStatusResponse `json:"jobs"`
}

func postMultipartDocument(t *testing.T, path string, filename string, content []byte) *http.Response {
	t.Helper()

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		t.Fatalf("create form file failed: %v", err)
	}
	if _, err := part.Write(content); err != nil {
		t.Fatalf("write file content failed: %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close writer failed: %v", err)
	}

	return doRequest(t, http.MethodPost, path, body.Bytes(), writer.FormDataContentType())
}

func TestUploadAndListDocumentsEndpoints(t *testing.T) {
	uploadResp := postMultipartDocument(t, "/api/documents/upload", "go-upload.txt", []byte("hello from go"))
	if uploadResp.StatusCode != http.StatusCreated {
		defer uploadResp.Body.Close()
		t.Fatalf("unexpected upload status: got %d, want %d", uploadResp.StatusCode, http.StatusCreated)
	}

	var uploadPayload documentUploadResponse
	decodeJSON(t, uploadResp, &uploadPayload)
	if strings.TrimSpace(uploadPayload.DocumentID) == "" {
		t.Fatal("expected non-empty document_id")
	}
	if uploadPayload.Status != "uploaded" {
		t.Fatalf("unexpected upload status value: %q", uploadPayload.Status)
	}

	listResp := doRequest(t, http.MethodGet, "/api/documents", nil, "")
	if listResp.StatusCode != http.StatusOK {
		defer listResp.Body.Close()
		t.Fatalf("unexpected list status: got %d, want %d", listResp.StatusCode, http.StatusOK)
	}

	var listPayload documentListResponse
	decodeJSON(t, listResp, &listPayload)
	found := false
	for _, item := range listPayload.Documents {
		if item.DocumentID == uploadPayload.DocumentID {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("uploaded document %s not found in list", uploadPayload.DocumentID)
	}
}

func TestUploadEmptyFileReturnsValidationError(t *testing.T) {
	resp := postMultipartDocument(t, "/api/documents/upload", "empty.txt", []byte{})
	assertErrorCode(t, resp, http.StatusBadRequest, "empty_file")
}

func TestUploadUnsupportedFileTypeReturnsValidationError(t *testing.T) {
	resp := postMultipartDocument(t, "/api/documents/upload", "archive.bin", []byte("not supported"))
	assertErrorCode(t, resp, http.StatusBadRequest, "invalid_file_type")
}

func TestUploadSpoofedPDFReturnsValidationError(t *testing.T) {
	resp := postMultipartDocument(t, "/api/documents/upload", "spoofed.pdf", []byte("not a real pdf"))
	assertErrorCode(t, resp, http.StatusBadRequest, "invalid_file_type")
}

func TestUploadTooLargeReturnsValidationError(t *testing.T) {
	largeContent := bytes.Repeat([]byte("a"), 26*1024*1024)
	resp := postMultipartDocument(t, "/api/documents/upload", "large.txt", largeContent)
	assertErrorCode(t, resp, http.StatusRequestEntityTooLarge, "file_too_large")
}

func TestStartIndexAndGetJobStatusEndpoints(t *testing.T) {
	uploadResp := postMultipartDocument(t, "/api/documents/upload", "index-me.txt", []byte("index me please"))
	if uploadResp.StatusCode != http.StatusCreated {
		defer uploadResp.Body.Close()
		t.Fatalf("unexpected upload status: got %d, want %d", uploadResp.StatusCode, http.StatusCreated)
	}

	var uploadPayload documentUploadResponse
	decodeJSON(t, uploadResp, &uploadPayload)

	indexPath := fmt.Sprintf("/api/documents/%s/index", uploadPayload.DocumentID)
	indexResp := doRequest(t, http.MethodPost, indexPath, nil, "")
	if indexResp.StatusCode != http.StatusAccepted {
		defer indexResp.Body.Close()
		t.Fatalf("unexpected index start status: got %d, want %d", indexResp.StatusCode, http.StatusAccepted)
	}

	var indexPayload documentIndexResponse
	decodeJSON(t, indexResp, &indexPayload)
	if strings.TrimSpace(indexPayload.JobID) == "" {
		t.Fatal("expected non-empty job_id")
	}

	jobResp := doRequest(t, http.MethodGet, "/api/jobs/"+indexPayload.JobID, nil, "")
	if jobResp.StatusCode != http.StatusOK {
		defer jobResp.Body.Close()
		t.Fatalf("unexpected job status code: got %d, want %d", jobResp.StatusCode, http.StatusOK)
	}

	var jobPayload jobStatusResponse
	decodeJSON(t, jobResp, &jobPayload)
	if jobPayload.JobID != indexPayload.JobID {
		t.Fatalf("job_id mismatch: got %s want %s", jobPayload.JobID, indexPayload.JobID)
	}

	allowedStatuses := map[string]bool{
		"queued":  true,
		"running": true,
		"done":    true,
		"failed":  true,
	}
	if !allowedStatuses[jobPayload.Status] {
		t.Fatalf("unexpected job status %q", jobPayload.Status)
	}
}

func TestGetMissingJobReturnsNotFound(t *testing.T) {
	resp := doRequest(t, http.MethodGet, "/api/jobs/missing-job-id", nil, "")
	assertErrorCode(t, resp, http.StatusNotFound, "job_not_found")
}

func TestListJobsEndpoint(t *testing.T) {
	uploadResp := postMultipartDocument(t, "/api/documents/upload", "jobs-list.txt", []byte("job list check"))
	if uploadResp.StatusCode != http.StatusCreated {
		defer uploadResp.Body.Close()
		t.Fatalf("unexpected upload status: got %d, want %d", uploadResp.StatusCode, http.StatusCreated)
	}

	var uploadPayload documentUploadResponse
	decodeJSON(t, uploadResp, &uploadPayload)

	indexPath := fmt.Sprintf("/api/documents/%s/index", uploadPayload.DocumentID)
	indexResp := doRequest(t, http.MethodPost, indexPath, nil, "")
	if indexResp.StatusCode != http.StatusAccepted {
		defer indexResp.Body.Close()
		t.Fatalf("unexpected index start status: got %d, want %d", indexResp.StatusCode, http.StatusAccepted)
	}
	indexResp.Body.Close()

	listResp := doRequest(t, http.MethodGet, "/api/jobs", nil, "")
	if listResp.StatusCode != http.StatusOK {
		defer listResp.Body.Close()
		t.Fatalf("unexpected jobs list status: got %d, want %d", listResp.StatusCode, http.StatusOK)
	}

	var listPayload jobListResponse
	decodeJSON(t, listResp, &listPayload)
	if len(listPayload.Jobs) == 0 {
		t.Fatal("expected non-empty jobs list")
	}
}

func TestMultipartUploadRejectsJSONContentType(t *testing.T) {
	resp := doRequest(t, http.MethodPost, "/api/documents/upload", []byte(`{"x":1}`), "application/json")
	if resp.StatusCode != http.StatusBadRequest && resp.StatusCode != http.StatusUnprocessableEntity {
		defer resp.Body.Close()
		t.Fatalf("unexpected status for non-multipart upload: %d", resp.StatusCode)
	}
	resp.Body.Close()
}

func TestUploadResponseIsValidJSON(t *testing.T) {
	resp := postMultipartDocument(t, "/api/documents/upload", "json-check.txt", []byte("abc"))
	if resp.StatusCode != http.StatusCreated {
		defer resp.Body.Close()
		t.Fatalf("unexpected upload status: %d", resp.StatusCode)
	}
	defer resp.Body.Close()

	var generic map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&generic); err != nil {
		t.Fatalf("failed to decode upload JSON: %v", err)
	}
}
