package tests

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFrontendDoesNotUseInnerHTML(t *testing.T) {
	root := filepath.Join("..", "frontend", "src")
	if _, err := os.Stat(root); err != nil {
		root = filepath.Join("frontend", "src")
	}
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			return nil
		}

		ext := filepath.Ext(path)
		if ext != ".ts" && ext != ".tsx" {
			return nil
		}

		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if strings.Contains(string(content), "innerHTML") {
			t.Errorf("found innerHTML usage in %s", path)
		}
		return nil
	})

	if err != nil {
		t.Fatalf("scan frontend sources failed: %v", err)
	}
}
