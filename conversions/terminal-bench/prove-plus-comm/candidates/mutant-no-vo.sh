#!/bin/sh
# A correct proof that is never compiled, so plus_comm.vo does not exist.
# The Evaluation's own coqc run would create it; this checks the existence
# check reads the candidate, as upstream's test runs before it compiles.
cd /workspace || exit 1
cat > plus_comm.v <<'COQ'
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
