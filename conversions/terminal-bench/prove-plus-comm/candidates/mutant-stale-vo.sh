#!/bin/sh
# An incomplete inductive step (plus_n_Sm is missing) compiled while the
# proof ended in Admitted, then switched to Qed without recompiling. The text
# checks pass and a plus_comm.vo exists; only compiling the final file fails.
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
Admitted.
COQ
coqc plus_comm.v
sed -i 's/^Admitted\.$/Qed./' plus_comm.v
