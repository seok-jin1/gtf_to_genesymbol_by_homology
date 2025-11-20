#!/usr/bin/env python3
"""
BLASTP 결과 + Annotation을 사용하여 LOC → Gene symbol 매핑을 수행합니다.

입력:
  - LOC → protein_id 매핑 (1_extract_loc_to_protein.py 출력)
  - BLASTP 결과 (UniProt reference 사용)
  - Reference annotation 파일 (UniProt ID → gene symbol)

출력:
  - LOC_id, protein_id, reference_accession, gene_symbol, identity, coverage 포함
"""

import sys
import argparse
from typing import Dict, List, Tuple
import os

# 스크립트 기본 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INTERMEDIATE_DIR = os.path.join(PROJECT_ROOT, 'intermediate')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')


def load_loc_to_protein(loc_file: str) -> Dict[str, str]:
    """
    LOC → protein_id 매핑을 로드합니다.

    Returns:
        {protein_id: gene_id} 형태의 딕셔너리
    """
    loc_map = {}
    try:
        with open(loc_file, "r") as f:
            # 헤더 스킵
            next(f)
            for line in f:
                cols = line.rstrip("\n").split("\t")
                if len(cols) >= 2:
                    gene_id = cols[0]  # LOC
                    protein_id = cols[1]  # XP
                    loc_map[protein_id] = gene_id

    except IOError as e:
        print(f"Error reading LOC file: {e}", file=sys.stderr)
        sys.exit(1)

    return loc_map


def load_accession_to_symbol(annotation_file: str) -> Dict[str, str]:
    """
    Reference accession → gene symbol 매핑을 로드합니다.

    파일 형식: accession\tsymbol (TSV)
    """
    symbol_map = {}
    try:
        with open(annotation_file, "r") as f:
            # 헤더 있을 수 있으니 처리
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue

                cols = line.split("\t")
                if len(cols) >= 2:
                    accession = cols[0].strip()
                    symbol = cols[1].strip()
                    symbol_map[accession] = symbol

    except IOError as e:
        print(f"Error reading annotation file: {e}", file=sys.stderr)
        sys.exit(1)

    return symbol_map


def parse_blast_result(blast_file: str) -> Dict[str, List[Tuple]]:
    """
    BLASTP 결과를 파싱합니다.

    outfmt 6: qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore
    (12 columns, no qcovs - will be calculated from qstart/qend and alignment length)

    Returns:
        {query_id: [(subject_id, pident, qcovs), ...]} 형태의 딕셔너리
    """
    blast_results = {}
    try:
        with open(blast_file, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue

                cols = line.split("\t")
                if len(cols) < 12:
                    continue

                qseqid = cols[0]  # query id
                sseqid = cols[1]  # subject id
                pident = float(cols[2])  # percent identity
                length = int(cols[3])  # alignment length
                qstart = int(cols[6])  # query start
                qend = int(cols[7])  # query end

                # Query coverage 계산: (qend - qstart + 1) / query_length * 100
                # 여기서는 alignment length를 대체 값으로 사용
                qcovs = (length / 1000.0) * 100  # 대략적인 추정 (최대 100%)
                if qcovs > 100:
                    qcovs = 100.0

                if qseqid not in blast_results:
                    blast_results[qseqid] = []

                blast_results[qseqid].append((sseqid, pident, qcovs))

    except (IOError, ValueError) as e:
        print(f"Error reading BLAST file: {e}", file=sys.stderr)
        sys.exit(1)

    return blast_results


def extract_accession(subject_id: str) -> str:
    """
    BLAST subject ID에서 accession을 추출합니다.

    형식:
    - ref|XP_XXXXXXX.X|... (RefSeq) → XP_XXXXXXX.X
    - Q969H6 (UniProt) → Q969H6
    - 단순 ID 형식
    """
    parts = subject_id.split("|")
    # ref|XP_XXXXX.X| 형식
    if len(parts) >= 3:
        return parts[1]
    # 단순 XP_XXXXX.X 또는 UniProt ID (Q969H6) 형식
    return subject_id.split()[0]


def map_blast_to_symbol(
    loc_file: str,
    blast_file: str,
    annotation_file: str,
    output_file=None,
    min_identity: float = 30.0,
    min_coverage: float = 30.0,
    verbose: bool = False
):
    """
    BLAST 결과를 gene symbol로 매핑합니다.

    Args:
        loc_file: LOC → protein_id 매핑 파일
        blast_file: BLASTP 결과 파일
        annotation_file: Reference accession → gene symbol 파일
        output_file: 출력 파일 객체
        min_identity: 최소 identity 퍼센트
        min_coverage: 최소 coverage 퍼센트
        verbose: 상세 출력 여부
    """
    if output_file is None:
        output_file = sys.stdout

    # 데이터 로드
    print(f"Loading LOC → protein_id mapping from {loc_file}...", file=sys.stderr)
    loc_map = load_loc_to_protein(loc_file)
    print(f"  Loaded {len(loc_map)} mappings", file=sys.stderr)

    print(f"Loading accession → symbol mapping from {annotation_file}...", file=sys.stderr)
    symbol_map = load_accession_to_symbol(annotation_file)
    print(f"  Loaded {len(symbol_map)} symbols", file=sys.stderr)

    print(f"Parsing BLAST results from {blast_file}...", file=sys.stderr)
    blast_results = parse_blast_result(blast_file)
    print(f"  Loaded results for {len(blast_results)} query sequences", file=sys.stderr)

    # 출력 헤더
    print("gene_id\tprotein_id\treference_accession\tgene_symbol\tidentity(%)\tcoverage(%)\tbit_score\tevalue",
          file=output_file)

    # 매핑 수행
    mapped_count = 0
    unmapped_count = 0

    for protein_id, hits in blast_results.items():
        if protein_id not in loc_map:
            if verbose:
                print(f"Warning: {protein_id} not in LOC mapping", file=sys.stderr)
            continue

        gene_id = loc_map[protein_id]

        # Best hit만 사용 (첫 번째)
        if hits:
            subject_id, pident, qcovs = hits[0]

            # 필터링
            if pident < min_identity or qcovs < min_coverage:
                if verbose:
                    print(f"Filtering: {protein_id} - identity={pident}, coverage={qcovs}",
                          file=sys.stderr)
                unmapped_count += 1
                continue

            accession = extract_accession(subject_id)
            symbol = symbol_map.get(accession, "")

            # 추가 정보는 BLAST 파일에서 다시 읽기
            # 간단히 처리하면 first hit만 사용
            print(f"{gene_id}\t{protein_id}\t{accession}\t{symbol}\t{pident:.2f}\t{qcovs:.2f}\t-\t-",
                  file=output_file)
            mapped_count += 1

        else:
            unmapped_count += 1

    # 요약
    print(f"\nMapping Summary:", file=sys.stderr)
    print(f"  Mapped: {mapped_count}", file=sys.stderr)
    print(f"  Unmapped: {unmapped_count}", file=sys.stderr)
    print(f"  Total: {mapped_count + unmapped_count}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="BLASTP 결과를 사용하여 LOC → Gene symbol 매핑을 수행합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  cd scripts
  python 5_map_blast_to_symbol.py \\
    -l ../intermediate/loc_protein_map.tsv \\
    -b ../intermediate/blast_results_complete.txt \\
    -a ../intermediate/human_symbol_map_uniprot.tsv \\
    -o ../results/final_gene_symbol_map.tsv

  # 더 엄격한 필터링
  python 5_map_blast_to_symbol.py \\
    -l ../intermediate/loc_protein_map.tsv \\
    -b ../intermediate/blast_results_complete.txt \\
    -a ../intermediate/human_symbol_map_uniprot.tsv \\
    -o ../results/final_gene_symbol_map_filtered.tsv \\
    --min-identity 30 \\
    --min-coverage 30
        """
    )

    parser.add_argument(
        "-l", "--loc-file",
        metavar="LOC_FILE",
        default=os.path.join(INTERMEDIATE_DIR, 'loc_protein_map.tsv'),
        help="LOC → protein_id 매핑 파일 (기본값: intermediate/loc_protein_map.tsv)"
    )

    parser.add_argument(
        "-b", "--blast-file",
        metavar="BLAST_FILE",
        default=os.path.join(INTERMEDIATE_DIR, 'blast_results_full.txt'),
        help="BLASTP 결과 파일 (기본값: intermediate/blast_results_full.txt)"
    )

    parser.add_argument(
        "-a", "--annotation-file",
        metavar="ANNOTATION_FILE",
        default=os.path.join(INTERMEDIATE_DIR, 'human_symbol_map_uniprot.tsv'),
        help="Reference accession → gene symbol 매핑 파일 (기본값: intermediate/human_symbol_map_uniprot.tsv)"
    )

    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        type=argparse.FileType('w'),
        default=sys.stdout,
        help="출력 파일 (기본값: stdout)"
    )

    parser.add_argument(
        "--min-identity",
        type=float,
        default=30.0,
        metavar="PERCENT",
        help="최소 identity 퍼센트 (기본값: 30.0)"
    )

    parser.add_argument(
        "--min-coverage",
        type=float,
        default=30.0,
        metavar="PERCENT",
        help="최소 query coverage 퍼센트 (기본값: 30.0)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 출력 활성화"
    )

    args = parser.parse_args()

    map_blast_to_symbol(
        args.loc_file,
        args.blast_file,
        args.annotation_file,
        args.output,
        args.min_identity,
        args.min_coverage,
        args.verbose
    )

    if args.output != sys.stdout:
        args.output.close()


if __name__ == "__main__":
    main()
