#!/bin/sh
# A correct, compiled proof with a Latin-1 byte (0xE9) in a comment. coqc
# accepts it, but upstream reads the file as UTF-8 and fails; this checks the
# Oracle's text reading matches upstream's decoding.
cd /workspace || exit 1
{
  printf '(* Commutativit\351 de l addition *)\n'
  cat <<'COQ'
Require Import Arith.

Theorem plus_comm : forall n m : nat,
  n + m = m + n.
Proof.
  intros n m.
  induction n as [|n' IHn'].
  - simpl.
    rewrite <- plus_n_O.
    reflexivity.
  - simpl.
    rewrite IHn'.
    rewrite plus_n_Sm.
    reflexivity.
Qed.
COQ
} > plus_comm.v
coqc plus_comm.v
