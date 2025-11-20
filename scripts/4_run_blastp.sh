#!/bin/bash

# BLASTP 실행
# Query FASTA와 Reference DB를 사용하여 동형 검색을 수행합니다.

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 기본값
EVALUE=1e-5
THREADS=4
OUTFMT="6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore qcovs"
MAX_HITS=5

# 함수 정의
print_usage() {
    cat << EOF
사용법: bash 4_run_blastp.sh -q QUERY -d DATABASE [옵션]

필수 인자:
  -q, --query FILE          Query FASTA 파일
  -d, --database DB         BLAST 데이터베이스 경로

옵션:
  -o, --output FILE         출력 파일 (기본값: query_basename.blastp.txt)
  -e, --evalue VALUE        E-value threshold (기본값: 1e-5)
  -t, --threads NUM         사용할 스레드 수 (기본값: 4)
  -m, --max-hits NUM        최대 hit 수 (기본값: 5)
  -h, --help                도움말 표시

예시:
  bash 4_run_blastp.sh -q shrimp_proteins.fasta -d blast_db/reference_proteome
  bash 4_run_blastp.sh -q shrimp.fa -d ref_db -e 1e-10 -t 8 -o results.txt
EOF
    exit 0
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -q|--query)
            QUERY="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -e|--evalue)
            EVALUE="$2"
            shift 2
            ;;
        -t|--threads)
            THREADS="$2"
            shift 2
            ;;
        -m|--max-hits)
            MAX_HITS="$2"
            shift 2
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

# 필수 인자 확인
if [ -z "$QUERY" ] || [ -z "$DATABASE" ]; then
    echo -e "${RED}Error: -q (query) and -d (database) are required${NC}"
    print_usage
fi

# 파일 존재 확인
if [ ! -f "$QUERY" ]; then
    echo -e "${RED}Error: Query file not found: $QUERY${NC}"
    exit 1
fi

if [ ! -f "${DATABASE}.phr" ]; then
    echo -e "${RED}Error: Database not found: $DATABASE${NC}"
    echo "Please run: bash 3_prepare_blast_db.sh"
    exit 1
fi

# 출력 파일명 설정
if [ -z "$OUTPUT" ]; then
    QUERY_BASE=$(basename "$QUERY" | sed 's/\.[^.]*$//')
    OUTPUT="${QUERY_BASE}.blastp.txt"
fi

echo -e "${GREEN}=== BLASTP 실행 ===${NC}"
echo "Query: $QUERY"
echo "Database: $DATABASE"
echo "Output: $OUTPUT"
echo "E-value: $EVALUE"
echo "Threads: $THREADS"
echo "Max hits: $MAX_HITS"

# BLASTP 실행
echo -e "${YELLOW}검색 중...${NC}"

blastp \
    -query "$QUERY" \
    -db "$DATABASE" \
    -out "$OUTPUT" \
    -evalue "$EVALUE" \
    -num_threads "$THREADS" \
    -num_alignments "$MAX_HITS" \
    -num_descriptions "$MAX_HITS" \
    -outfmt "$OUTFMT"

echo -e "${GREEN}=== 완료! ===${NC}"
echo "결과 파일: $OUTPUT"
echo ""
echo "결과 요약:"
wc -l "$OUTPUT"
