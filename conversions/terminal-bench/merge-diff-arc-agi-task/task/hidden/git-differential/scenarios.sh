#!/bin/bash
# The 71 repositories of the comparison; see compare.py for how to run it.
set +e
G=/app/repo/.git
mk(){ rm -rf /app/repo /app/.git /app/other.git /app/tmpg; mkdir -p /app/repo; cd /app/repo; git init -q; git fetch -q /app/bundle1.bundle HEAD:branch1; git fetch -q /app/bundle2.bundle HEAD:branch2; cd /; }
t(){ python3 -B /diff/compare.py "$1"; }
B1=c8dca82d38e152cd58eb0b31394af08f37c1385a
mk; t normal
mk; git -C /app/repo pack-refs --all; t packed
mk; git -C /app/repo pack-refs --all; echo $B1 > $G/refs/heads/branch1; t packed_plus_loose
mk; git -C /app/repo gc -q; t gc
mk; git -C /app/repo -c user.email=a@b -c user.name=a checkout -q branch1; git -C /app/repo -c user.email=a@b -c user.name=a merge -q -X theirs branch2 -m m; t merged
mk; echo 0123456789012345678901234567890123456789 > $G/refs/heads/missingobj; t missingobj
mk; echo 836b057 > $G/refs/heads/branch2; t short_branch2
mk; echo "ref: refs/heads/nothere" > $G/refs/heads/dsym; t danglingsym
mk; echo "ref: refs/heads/branch1" > $G/refs/heads/gsym; t goodsym
mk; mkdir -p $G/refs/remotes/o; echo "ref: refs/remotes/o/x" > $G/refs/remotes/o/HEAD; echo $B1 > $G/refs/remotes/o/x; t remotesym
mk; echo 0000000000000000000000000000000000000000 > $G/refs/heads/nulloid; t nulloid
mk; printf '%s\n' "# pack-refs with: peeled" "0000000000000000000000000000000000000000 refs/heads/pnull" > $G/packed-refs; t packednull
mk; echo "${B1}x" > $G/refs/heads/branch2; t trailing
mk; echo "$B1 x" > $G/refs/heads/zz; t trailingspace
mk; printf '%s' "$B1" > $G/refs/heads/nonl; t nonewline
mk; git -C /app/repo checkout -q --detach branch2; t detached
mk; git -C /app/repo tag branch1x branch1; git -C /app/repo branch -q -D branch1; t tagonly
mk; git -C /app/repo update-ref refs/remotes/b/branch1 branch1; git -C /app/repo update-ref -d refs/heads/branch1; t remote_only
mk; git -C /app/repo config core.repositoryformatversion 2; t v2
mk; git -C /app/repo config core.repositoryformatversion 1; git -C /app/repo config extensions.foo bar; t v1unknown
mk; git -C /app/repo config core.repositoryformatversion 1; git -C /app/repo config extensions.worktreeConfig true; t v1wtconfig
mk; git -C /app/repo config core.repositoryformatversion 0; git -C /app/repo config extensions.objectformat sha1; t v0objfmt
mk; git -C /app/repo config core.repositoryformatversion 0; git -C /app/repo config extensions.foo bar; t v0unknown
mk; git -C /app/repo config core.repositoryformatversion 0x1; t vhex
mk; git -C /app/repo config core.repositoryformatversion 1k; t vk
mk; echo "[core" >> $G/config; t badconfig
mk; printf '[core]\n\trepositoryformatversion = 2 # c\n' >> $G/config; t config_comment
mk; printf '[core]\n\tfoo # c\n' >> $G/config; t config_key_comment
mk; printf '[remote "a\\"b"]\n\turl = "x;y" ; z\n' >> $G/config; t config_quoted
mk; printf '[core]\n\tx = "unterminated\n' >> $G/config; t config_unterminated
mk; printf '[core]\n\tx = a\\qb\n' >> $G/config; t config_badescape
mk; printf '[core]\n\trepositoryformatversion\n' >> $G/config; t config_novalue
mk; printf '1bad = x\n' >> $G/config; t config_badkey
mk; git -C /app/repo config core.repositoryformatversion abc; t badversion
mk; mv $G /app/other.git; echo "gitdir: ../other.git" > $G; t gitfile
mk; mv $G /app/other.git; echo "gitdir: /app/nothere" > $G; t gitfile_bad
mk; mv $G /app/other.git; : > $G; t emptygitfile
mk; mv $G /app/.git; mkdir $G; t parentrepo
mk; mv $G /app/.git; t parentrepo_nodotgit
mk; rm $G/HEAD; t noHEAD
mk; mv $G /app/tmpg; mv /app/tmpg/* /app/repo/; mkdir $G; t bareinrepo
mk; rm -rf $G/objects; t noobjects
mk; echo "ref:refs/heads/x" > $G/HEAD; t headnospace
mk; echo "ref: heads/x" > $G/HEAD; t headbad
mk; echo "$B1" > $G/HEAD; t headoid
mk; rm $G/HEAD; ln -s refs/heads/branch1 $G/HEAD; t headsymlink
mk; mkdir -p "$G/refs/heads/a b"; echo $B1 > "$G/refs/heads/a b/x"; echo $B1 > $G/refs/heads/.hidden; echo $B1 > $G/refs/heads/z.lock; echo $B1 > "$G/refs/heads/q~1"; t badnames
mk; ln -s refs/heads/branch1 $G/refs/heads/lnk; t symlinkref
mk; mkdir -p $G/refs/heads/dir; ln -s /app/repo/.git/refs/heads/branch1 $G/refs/heads/abslnk; t abssymlinkref
mk; printf '%s\n' "garbage" > $G/packed-refs; t packed_garbage
mk; printf '%s' "$B1 refs/heads/p" > $G/packed-refs; t packed_unterminated
mk; printf '%s\n' "# hello" > $G/packed-refs; t packed_comment
mk; printf '%s\n' "$B1 refs/heads/p" "^$B1" > $G/packed-refs; t packed_peel
mk; printf '%s\n' "^$B1" > $G/packed-refs; t packed_peel_first
mk; printf '%s\n' "$B1 refs/heads/b a d" > $G/packed-refs; t packed_badname
mk; git -C /app/repo worktree add -q /app/repo/wt branch2 2>/dev/null; t worktree
mk; git -C /app/repo config core.repositoryformatversion 1; git -C /app/repo config extensions.objectformat sha256; t sha256_ext
rm -rf /app/repo; t norepo
mkdir -p /app; : > /app/repo; t repofile; rm -f /app/repo
mkdir -p /app/repo; t emptydir
mk; ln -s /app/repo/.git/refs/heads/branch1 $G/refs/heads/abslnk; ln -s branch1 $G/refs/heads/rellnk; mkdir -p /app/x; ln -s /app/x $G/refs/heads/dirlnk; git -C /app/repo rev-parse branch1 > /app/x/inner; t symlinks2
mk; ln -s . $G/refs/heads/loop; t symlinkloop
mk; ln -s refs/heads/branch1 $G/refs/heads/branch1b; t symlink_refs_prefix
mk; printf '%s\f\n' "$B1" > $G/refs/heads/branch2; t oid_formfeed
mk; printf '%s\v\n' "$B1" > $G/refs/heads/branch2; t oid_vtab
mk; printf '%s\r\n' "$B1" > $G/refs/heads/branch2; t oid_cr
mk; printf 'ref:\frefs/heads/branch1\n' > $G/refs/heads/fsym; t symref_formfeed
mk; printf 'ref:\trefs/heads/branch1\n' > $G/refs/heads/tsym; t symref_tab
mk; printf 'ref:\frefs/heads/branch1\n' > $G/HEAD; t head_formfeed
mk; printf '\f[core]\n' >> $G/config; t config_formfeed
mk; printf '[core]\n\tx = a\rb\n' >> $G/config; t config_cr_value
