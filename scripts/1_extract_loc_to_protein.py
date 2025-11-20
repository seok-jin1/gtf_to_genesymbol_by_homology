#!/usr/bin/env python3
"""
GTF 파일에서 LOC (gene_id) → Protein ID (XP) 매핑을 추출합니다.

GTF의 CDS feature에서 다음 정보를 추출:
  - gene_id (LOC135219088 형식)
  - protein_id (XP_064111589.1 형식)
  - product (단백질 설명)

출력: TSV 형식 (gene_id, protein_id, product, transcript_id)
"""

import sys
import re
import argparse
import os

# 스크립트 기본 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
INTERMEDIATE_DIR = os.path.join(PROJECT_ROOT, 'intermediate')


def parse_attributes(attr_field: str) -> dict:
    """GTF 9번째 컬럼을 dict로 파싱."""
    attrs = {}
    for item in attr_field.strip().strip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        # key "value" 형식 파싱
        m = re.match(r'([^ ]+)\s+"(.+)"', item)
        if m:
            key, val = m.group(1), m.group(2)
            attrs[key] = val
    return attrs


def extract_loc_to_protein(gtf_path: str, output_file=None):
    """
    GTF 파일에서 LOC → protein_id 매핑을 추출합니다.

    Args:
        gtf_path: 입력 GTF 파일 경로
        output_file: 출력 파일 객체 (기본값: stdout)
    """
    if output_file is None:
        output_file = sys.stdout

    print("gene_id\tprotein_id\tproduct\ttranscript_id", file=output_file)

    seen_pairs = set()  # (gene_id, protein_id) 쌍의 중복 제거

    try:
        with open(gtf_path, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue

                cols = line.split("\t")
                if len(cols) < 9:
                    continue

                feature = cols[2]
                attrs_str = cols[8]

                # CDS feature만 처리 (protein_id는 CDS에만 있음)
                if feature != "CDS":
                    continue

                attrs = parse_attributes(attrs_str)
                gene_id = attrs.get("gene_id")
                protein_id = attrs.get("protein_id")
                transcript_id = attrs.get("transcript_id", "")
                product = attrs.get("product", "")

                # protein_id가 없으면 스킵
                if not gene_id or not protein_id:
                    continue

                # 중복 쌍 제거
                pair = (gene_id, protein_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                # 출력
                print(f"{gene_id}\t{protein_id}\t{product}\t{transcript_id}", file=output_file)

    except IOError as e:
        print(f"Error reading GTF file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="GTF 파일에서 LOC (gene_id) → Protein ID (XP) 매핑을 추출합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  cd scripts && python 1_extract_loc_to_protein.py
  cd scripts && python 1_extract_loc_to_protein.py -o ../intermediate/loc_protein_map.tsv
  cd scripts && python 1_extract_loc_to_protein.py data/annotation.gtf | head -20
        """
    )

    parser.add_argument(
        "gtf_file",
        metavar="GTF_FILE",
        nargs='?',
        default=os.path.join(DATA_DIR, 'annotation.gtf'),
        help="입력 GTF 파일 경로 (기본값: data/annotation.gtf)"
    )

    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        type=argparse.FileType('w'),
        default=sys.stdout,
        help="출력 TSV 파일 경로 (기본값: stdout)"
    )

    args = parser.parse_args()

    extract_loc_to_protein(args.gtf_file, args.output)

    if args.output != sys.stdout:
        args.output.close()


if __name__ == "__main__":
    main()
