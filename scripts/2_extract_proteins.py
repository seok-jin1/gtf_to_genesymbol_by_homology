#!/usr/bin/env python3
"""
FASTA 파일에서 특정 ID의 단백질 서열을 추출합니다.

입력:
  - FASTA 파일
  - ID 리스트 (텍스트 파일 또는 TSV의 특정 컬럼)

출력:
  - 필터링된 FASTA 파일
"""

import sys
import argparse
from typing import Set
import os

# 스크립트 기본 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INTERMEDIATE_DIR = os.path.join(PROJECT_ROOT, 'intermediate')


def load_ids_from_file(id_file: str, column: int = 0) -> Set[str]:
    """
    ID 리스트 파일에서 ID를 읽습니다.

    Args:
        id_file: ID 리스트 파일 (텍스트 또는 TSV)
        column: TSV인 경우 몇 번째 컬럼을 사용할지 (0-indexed)

    Returns:
        ID 집합
    """
    ids = set()
    try:
        with open(id_file, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue

                # TSV 파일인 경우 특정 컬럼만 추출
                if "\t" in line:
                    cols = line.split("\t")
                    if column < len(cols):
                        ids.add(cols[column].strip())
                else:
                    ids.add(line.strip())

    except IOError as e:
        print(f"Error reading ID file: {e}", file=sys.stderr)
        sys.exit(1)

    return ids


def extract_sequences(fasta_file: str, id_set: Set[str], output_file, verbose: bool = False):
    """
    FASTA 파일에서 ID 리스트에 해당하는 서열을 추출합니다.

    Args:
        fasta_file: 입력 FASTA 파일
        id_set: 추출할 ID 집합
        output_file: 출력 파일 객체
        verbose: 진행상황 출력 여부
    """
    found_count = 0
    not_found_ids = set(id_set)
    current_id = None
    current_seq = []

    try:
        with open(fasta_file, "r") as f:
            for line in f:
                line = line.rstrip("\n")

                if line.startswith(">"):
                    # 이전 서열 처리
                    if current_id and current_id in id_set:
                        seq_str = "".join(current_seq)
                        print(f">{current_id}", file=output_file)
                        # 80자씩 끊어서 출력 (표준 FASTA 형식)
                        for i in range(0, len(seq_str), 80):
                            print(seq_str[i:i+80], file=output_file)
                        found_count += 1
                        if verbose:
                            print(f"Found: {current_id}", file=sys.stderr)

                    # Header에서 ID 추출
                    header = line[1:].strip()
                    # 첫 번째 공백까지가 ID (대부분의 FASTA 형식)
                    current_id = header.split()[0] if header else None

                    if current_id and current_id in not_found_ids:
                        not_found_ids.discard(current_id)

                    current_seq = []

                else:
                    # 서열 추가
                    current_seq.append(line)

            # 마지막 서열 처리
            if current_id and current_id in id_set:
                seq_str = "".join(current_seq)
                print(f">{current_id}", file=output_file)
                for i in range(0, len(seq_str), 80):
                    print(seq_str[i:i+80], file=output_file)
                found_count += 1
                if verbose:
                    print(f"Found: {current_id}", file=sys.stderr)

    except IOError as e:
        print(f"Error reading FASTA file: {e}", file=sys.stderr)
        sys.exit(1)

    # 요약 출력
    print(f"Statistics:", file=sys.stderr)
    print(f"  Total IDs requested: {len(id_set)}", file=sys.stderr)
    print(f"  IDs found: {found_count}", file=sys.stderr)
    print(f"  IDs not found: {len(not_found_ids)}", file=sys.stderr)

    if not_found_ids and len(not_found_ids) <= 20:
        print(f"  Missing IDs: {', '.join(sorted(not_found_ids))}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="FASTA 파일에서 특정 ID의 단백질 서열을 추출합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  cd scripts
  # FASTA + ID 리스트 (column 1 = protein_id)
  python 2_extract_proteins.py ../intermediate/proteins.fasta ../intermediate/loc_protein_map.tsv -c 1

  # 출력 파일 지정
  python 2_extract_proteins.py ../intermediate/proteins.fasta ../intermediate/loc_protein_map.tsv -c 1 -o ../intermediate/shrimp_query.fasta

  # 상세 출력
  python 2_extract_proteins.py ../intermediate/proteins.fasta ../intermediate/loc_protein_map.tsv -c 1 -v
        """
    )

    parser.add_argument(
        "fasta_file",
        metavar="FASTA_FILE",
        help="입력 FASTA 파일 경로"
    )

    parser.add_argument(
        "id_file",
        metavar="ID_FILE",
        help="추출할 ID 리스트 (텍스트 또는 TSV 파일)"
    )

    parser.add_argument(
        "-c", "--column",
        type=int,
        default=0,
        metavar="COL",
        help="TSV 파일의 경우 몇 번째 컬럼을 사용할지 (기본값: 0)"
    )

    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        type=argparse.FileType('w'),
        default=sys.stdout,
        help="출력 FASTA 파일 경로 (기본값: stdout)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 출력 활성화"
    )

    args = parser.parse_args()

    # ID 로드
    id_set = load_ids_from_file(args.id_file, args.column)
    print(f"Loaded {len(id_set)} IDs from {args.id_file}", file=sys.stderr)

    # 서열 추출
    extract_sequences(args.fasta_file, id_set, args.output, args.verbose)

    if args.output != sys.stdout:
        args.output.close()


if __name__ == "__main__":
    main()
