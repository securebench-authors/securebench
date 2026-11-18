#!/bin/sh
# A correct, compiled proof whose UTF-8 plus_comm.v loads a helper file with a
# Latin-1 byte in a warning name. coqc exits 0 but prints the raw byte, so
# upstream's subprocess.run(text=True) raises; this checks the adapter's
# output_utf8 report and the Oracle's use of it.
cd /workspace || exit 1
printf 'Set Warnings "+caf\351".\n' > notes.v
cat > plus_comm.v <<'COQ'
Load notes.
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
coqc plus_comm.v
