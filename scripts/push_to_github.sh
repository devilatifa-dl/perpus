#!/usr/bin/env bash
# Kirim perubahan di /app ke GitHub (devilatifa-dl/perpus) dengan aman.
#
#   bash /app/scripts/push_to_github.sh --dry-run <branch>          # lihat dulu apa yang berubah
#   bash /app/scripts/push_to_github.sh <branch> "pesan commit"      # commit + push
#
# - Token dibaca dari GITHUB_TOKEN di /app/backend/.env (tidak pernah ditulis ke .git/config / log).
# - Riwayat git /app (milik workspace) tidak disentuh; sinkronisasi lewat salinan terpisah di /root/perpus-github.
# - File .env, node_modules, build tidak pernah ikut terkirim; push dibatalkan bila ada kunci rahasia terdeteksi.
set -euo pipefail

REPO="devilatifa-dl/perpus"
SRC="/app"
WORK="/root/perpus-github"

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
BRANCH="${1:-}"
MSG="${2:-}"
if [ -z "$BRANCH" ]; then echo "Pakai: $0 [--dry-run] <branch> \"pesan commit\""; exit 1; fi
if [ "$DRY" = 0 ] && [ -z "$MSG" ]; then echo "Pesan commit wajib diisi."; exit 1; fi

GITHUB_TOKEN="$(grep -E '^GITHUB_TOKEN=' "$SRC/backend/.env" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"
if [ -z "$GITHUB_TOKEN" ]; then echo "GITHUB_TOKEN belum diatur."; exit 1; fi
export GITHUB_TOKEN

# Credential helper sementara: token diambil dari environment, tidak disimpan di disk.
git_auth() {
  git -c credential.helper= \
      -c credential.helper='!f() { echo username=x-access-token; echo "password=$GITHUB_TOKEN"; }; f' \
      -c user.name="Emergent Agent" -c user.email="github@emergent.sh" "$@"
}

if [ ! -d "$WORK/.git" ]; then
  git_auth clone -q "https://github.com/$REPO.git" "$WORK"
fi
cd "$WORK"
git remote set-url origin "https://github.com/$REPO.git"
git_auth fetch -q origin --prune
git reset -q --hard
git clean -qfd

if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  git checkout -q -B "$BRANCH" "origin/$BRANCH"
else
  DEFAULT="$(git symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##')"
  git checkout -q -B "$BRANCH" "origin/$DEFAULT"
  echo "Branch baru '$BRANCH' dibuat dari '$DEFAULT'."
fi

rsync -a --delete \
  --exclude='.git/' --exclude='.emergent/' --exclude='.env' --exclude='.env.*' --exclude='*.env' \
  --exclude='node_modules/' --exclude='build/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
  --exclude='/yarn.lock' --exclude='*.log' \
  "$SRC/" "$WORK/"

git add -A
if git diff --cached --quiet; then echo "Tidak ada perubahan dibanding GitHub ($BRANCH)."; exit 0; fi

# Cegah kebocoran kunci rahasia.
SECRETS=("$GITHUB_TOKEN")
for k in EMERGENT_LLM_KEY EMERGENT_EMAIL_KEY JWT_SECRET; do
  v="$(grep -E "^$k=" "$SRC/backend/.env" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"
  [ -n "$v" ] && SECRETS+=("$v")
done
for s in "${SECRETS[@]}"; do
  if git diff --cached | grep -qF -- "$s"; then
    echo "DIBATALKAN: kunci rahasia terdeteksi di perubahan. Tidak ada yang dikirim."
    git reset -q --hard; exit 2
  fi
done

echo "Perubahan yang akan dikirim ke $REPO ($BRANCH):"
git diff --cached --stat | tail -n 40

if [ "$DRY" = 1 ]; then git reset -q --hard; echo "(dry-run: tidak ada yang dikirim)"; exit 0; fi

git_auth commit -q -m "$MSG"
git_auth push -q origin "$BRANCH"
echo "Terkirim: $(git log -1 --format='%h %s') -> https://github.com/$REPO/tree/$BRANCH"
