#!/bin/sh
# A correct, compiled proof whose comment still mentions "admit". Upstream's
# substring test rejects it; this checks the Oracle searches the whole text,
# comments included, exactly as upstream's `"admit" not in content` does.
cd /workspace || exit 1
cat > plus_comm.v <<'COQ'
Require Import Arith.

Theorem plus_comm : forall n m : nat,
  n + m = m + n.
Proof.
  intros n m.
  induction n as [|n' IHn'].
  - simpl.
    (* base case: no admit needed any more *)
    rewrite <- plus_n_O.
    reflexivity.
  - simpl.
    rewrite IHn'.
    rewrite plus_n_Sm.
    reflexivity.
Qed.
COQ
coqc plus_comm.v
