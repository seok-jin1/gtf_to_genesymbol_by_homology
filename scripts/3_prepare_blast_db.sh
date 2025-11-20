#!/bin/bash

# BLASTP Reference Database 준비
# Human, Mouse, Drosophila 등의 reference proteome을 다운로드하고
# 단일 BLAST DB로 병합합니다.

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 기본값
WORK_DIR="."
OUTPUT_DIR="${WORK_DIR}/blast_db"
SKIP_DOWNLOAD=false

# 함수 정의
print_usage() {
    cat << EOF
사용법: bash 3_prepare_blast_db.sh [옵션]

옵션:
  -w, --workdir DIR         작업 디렉토리 (기본값: .)
  -o, --output DIR          출력 디렉토리 (기본값: \$WORKDIR/blast_db)
  -s, --skip-download       이미 다운로드한 파일 사용 (-s)
  -h, --help                도움말 표시

예시:
  bash 3_prepare_blast_db.sh
  bash 3_prepare_blast_db.sh -w /data/shrimp -o /data/blast_db
  bash 3_prepare_blast_db.sh --skip-download
EOF
    exit 0
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--workdir)
            WORK_DIR="$2"
            OUTPUT_DIR="${WORK_DIR}/blast_db"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--skip-download)
            SKIP_DOWNLOAD=true
            shift
            ;;
        -h|--help)
            print_usage
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            ;;
    esac
done

# 필수 도구 확인
check_dependencies() {
    local missing=false
    for cmd in makeblastdb; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "${RED}Error: $cmd not found. Please install BLAST+.${NC}"
            missing=true
        fi
    done
    if [ "$missing" = true ]; then
        exit 1
    fi
}

# 디렉토리 생성
mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}=== BLASTP Reference DB 준비 ===${NC}"
echo "작업 디렉토리: $WORK_DIR"
echo "출력 디렉토리: $OUTPUT_DIR"

# 의존성 확인
check_dependencies

# Reference FASTA 파일들
PROTEOMES=(
    "https://ftp.ncbi.nlm.nih.gov/refseq/H_sapiens/annotation/GRCh38_latest/refseq_identifiers/protein.fasta.gz:human"
    "https://ftp.ncbi.nlm.nih.gov/refseq/M_musculus/annotation/GRCm39_latest/refseq_identifiers/protein.fasta.gz:mouse"
    "https://ftp.ncbi.nlm.nih.gov/refseq/D_melanogaster/annotation/release-6_plus_ISO1_MT/refseq_identifiers/protein.fasta.gz:drosophila"
)

# 다운로드
echo -e "${YELLOW}[1/3] Reference proteome 다운로드 중...${NC}"

if [ "$SKIP_DOWNLOAD" = false ]; then
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT

    for entry in "${PROTEOMES[@]}"; do
        IFS=':' read -r url name <<< "$entry"
        echo "  다운로드: $name"
        wget -q -O "$TEMP_DIR/${name}.fasta.gz" "$url" || {
            echo -e "${RED}Warning: $name 다운로드 실패. 스킵합니다.${NC}"
        }
    done

    # 압축 해제 및 병합
    echo -e "${YELLOW}[2/3] 파일 압축 해제 및 병합 중...${NC}"
    MERGED_FASTA="${OUTPUT_DIR}/reference_proteome.fasta"
    > "$MERGED_FASTA"

    for file in "$TEMP_DIR"/*.fasta.gz; do
        if [ -f "$file" ]; then
            echo "  병합: $(basename $file)"
            zcat "$file" >> "$MERGED_FASTA"
        fi
    done
else
    MERGED_FASTA="${OUTPUT_DIR}/reference_proteome.fasta"
    if [ ! -f "$MERGED_FASTA" ]; then
        echo -e "${RED}Error: $MERGED_FASTA 파일이 없습니다.${NC}"
        exit 1
    fi
    echo "기존 파일 사용: $MERGED_FASTA"
fi

# 중복 제거 (선택사항)
echo -e "${YELLOW}[3/3] BLAST 데이터베이스 생성 중...${NC}"

# 임시 파일로 중복 제거된 버전 생성
TEMP_DEDUP=$(mktemp)
awk '!seen[$0]++' "$MERGED_FASTA" > "$TEMP_DEDUP"
mv "$TEMP_DEDUP" "$MERGED_FASTA"

# BLAST DB 생성
DB_NAME="${OUTPUT_DIR}/reference_proteome"
makeblastdb \
    -in "$MERGED_FASTA" \
    -dbtype prot \
    -out "$DB_NAME" \
    -parse_seqids \
    -title "Reference Proteome (Human, Mouse, Drosophila)"

echo -e "${GREEN}=== 완료! ===${NC}"
echo "BLAST DB location: $DB_NAME"
echo "사용법: blastp -db $DB_NAME -query query.fasta -out results.txt"
