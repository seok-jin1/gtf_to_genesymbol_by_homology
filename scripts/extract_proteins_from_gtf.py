#!/usr/bin/env python3
"""
GTF + genome FASTA에서 protein sequence를 추출합니다.

1. GTF 파싱: CDS feature에서 위치 정보 추출
2. 서열 추출: genome FASTA에서 해당 위치의 DNA 추출
3. 번역: DNA → codon → amino acid
4. protein_id별로 정렬
"""

import sys
import argparse
from typing import Dict, List, Tuple
import re
import os

# 스크립트 기본 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
INTERMEDIATE_DIR = os.path.join(PROJECT_ROOT, 'intermediate')

# 유전자 코드 (표준)
CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}


def parse_gtf_attributes(attr_field: str) -> dict:
    """GTF attribute 필드 파싱."""
    attrs = {}
    for item in attr_field.strip().strip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        m = re.match(r'([^ ]+)\s+"(.+)"', item)
        if m:
            key, val = m.group(1), m.group(2)
            attrs[key] = val
    return attrs


def load_genome_fasta(fasta_file: str) -> Dict[str, str]:
    """
    Genome FASTA 파일을 메모리에 로드합니다.
    주의: 대용량 파일이므로 메모리 사용량 확인 필요
    """
    sequences = {}
    current_id = None
    current_seq = []

    print(f"Loading genome FASTA from {fasta_file}...", file=sys.stderr)

    with open(fasta_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 1000000 == 0:
                print(f"  Processed {line_num:,} lines...", file=sys.stderr)

            line = line.rstrip("\n")

            if line.startswith(">"):
                # 이전 서열 저장
                if current_id:
                    sequences[current_id] = "".join(current_seq)

                # 새로운 ID 파싱
                header = line[1:].strip()
                current_id = header.split()[0]
                current_seq = []

            else:
                current_seq.append(line.upper())

        # 마지막 서열 저장
        if current_id:
            sequences[current_id] = "".join(current_seq)

    print(f"Loaded {len(sequences)} sequences", file=sys.stderr)
    return sequences


def extract_cds_regions(gtf_file: str) -> Dict[str, List[Tuple]]:
    """
    GTF 파일에서 CDS 영역을 추출합니다.

    Returns:
        {transcript_id: [(chrom, start, end, strand, frame, protein_id), ...]}
    """
    cds_regions = {}

    print(f"Parsing GTF from {gtf_file}...", file=sys.stderr)

    with open(gtf_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 100000 == 0:
                print(f"  Processed {line_num:,} lines...", file=sys.stderr)

            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue

            cols = line.split("\t")
            if len(cols) < 9:
                continue

            chrom, source, feature, start, end, score, strand, frame, attrs_str = cols

            # CDS feature만
            if feature != "CDS":
                continue

            attrs = parse_gtf_attributes(attrs_str)
            transcript_id = attrs.get("transcript_id")
            protein_id = attrs.get("protein_id")

            if not transcript_id or not protein_id:
                continue

            if transcript_id not in cds_regions:
                cds_regions[transcript_id] = []

            cds_regions[transcript_id].append((
                chrom,
                int(start) - 1,  # GTF는 1-based, Python은 0-based
                int(end),
                strand,
                int(frame),
                protein_id
            ))

    print(f"Found {len(cds_regions)} transcripts with CDS", file=sys.stderr)
    return cds_regions


def reverse_complement(seq: str) -> str:
    """DNA 서열의 보수 역순."""
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return "".join(complement.get(base, 'N') for base in reversed(seq))


def translate_cds(dna_seq: str) -> str:
    """DNA 서열을 단백질로 번역."""
    protein = []
    for i in range(0, len(dna_seq) - 2, 3):
        codon = dna_seq[i:i+3].upper()
        # N 포함된 코돈은 X로 번역
        if 'N' in codon or len(codon) < 3:
            protein.append('X')
        else:
            amino_acid = CODON_TABLE.get(codon, 'X')
            protein.append(amino_acid)

    return "".join(protein)


def extract_proteins(gtf_file: str, genome_file: str, output_file=None, verbose: bool = False):
    """
    GTF + genome에서 protein sequence를 추출합니다.
    """
    if output_file is None:
        output_file = sys.stdout

    # 1. Genome 로드
    sequences = load_genome_fasta(genome_file)

    # 2. CDS 영역 추출
    cds_regions = extract_cds_regions(gtf_file)

    # 3. 단백질 추출
    print(f"\nExtracting proteins...", file=sys.stderr)

    proteins_by_id = {}  # {protein_id: sequence}
    translated_count = 0
    error_count = 0

    for transcript_id, regions in cds_regions.items():
        try:
            # 각 CDS 영역별로 서열 추출
            cds_sequence_parts = []

            for chrom, start, end, strand, frame, protein_id in regions:
                if chrom not in sequences:
                    if verbose:
                        print(f"Warning: Chromosome {chrom} not found in genome", file=sys.stderr)
                    error_count += 1
                    continue

                # 서열 추출
                dna = sequences[chrom][start:end]

                # 역방향이면 보수 역순
                if strand == "-":
                    dna = reverse_complement(dna)

                cds_sequence_parts.append(dna)

            if not cds_sequence_parts:
                continue

            # CDS 서열 병합
            cds_sequence = "".join(cds_sequence_parts)

            # 번역
            protein_seq = translate_cds(cds_sequence)

            # protein_id별로 저장 (마지막 것이 기본값)
            if protein_id not in proteins_by_id:
                proteins_by_id[protein_id] = protein_seq
                translated_count += 1

        except Exception as e:
            if verbose:
                print(f"Error processing {transcript_id}: {e}", file=sys.stderr)
            error_count += 1

    # 4. FASTA 형식으로 출력
    print(f"Writing proteins to output...", file=sys.stderr)

    for protein_id in sorted(proteins_by_id.keys()):
        seq = proteins_by_id[protein_id]
        print(f">{protein_id}", file=output_file)

        # 80자씩 끊어서 출력
        for i in range(0, len(seq), 80):
            print(seq[i:i+80], file=output_file)

    # 통계
    print(f"\n=== Statistics ===", file=sys.stderr)
    print(f"Total proteins extracted: {translated_count}", file=sys.stderr)
    print(f"Errors: {error_count}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="GTF + Genome FASTA에서 protein sequence를 추출합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  cd scripts && python extract_proteins_from_gtf.py
  cd scripts && python extract_proteins_from_gtf.py -o ../intermediate/proteins.fasta -v
        """
    )

    parser.add_argument(
        "gtf_file",
        metavar="GTF_FILE",
        nargs='?',
        default=os.path.join(DATA_DIR, 'annotation.gtf'),
        help="입력 GTF 파일 (기본값: data/annotation.gtf)"
    )

    parser.add_argument(
        "genome_file",
        metavar="GENOME_FILE",
        nargs='?',
        default=os.path.join(DATA_DIR, 'genome.fna'),
        help="게놈 FASTA 파일 (기본값: data/genome.fna)"
    )

    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        type=argparse.FileType('w'),
        default=sys.stdout,
        help="출력 FASTA 파일 (기본값: stdout)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 출력"
    )

    args = parser.parse_args()

    extract_proteins(args.gtf_file, args.genome_file, args.output, args.verbose)

    if args.output != sys.stdout:
        args.output.close()


if __name__ == "__main__":
    main()
