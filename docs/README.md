# BLASTP Gene Symbol 매핑 파이프라인

쌩프(Macrobrachium nipponense) 유전자를 Human gene symbols로 매핑하는 완전 자동화 파이프라인

---

## 📋 프로젝트 개요

이 프로젝트는 다음을 수행합니다:

1. **GTF 파싱**: `annotation.gtf`에서 LOC gene ID ↔ Protein ID 추출
2. **Protein 추출**: `genome.fna`에서 DNA 서열을 Protein으로 번역
3. **Query 준비**: 추출된 단백질을 BLASTP 질의 형식으로 정리
4. **Reference DB 생성**: Human reference proteome에서 BLAST DB 구성
5. **BLASTP 실행**: 모든 쌩프 단백질을 Human orthologs에 매칭
6. **Symbol 매핑**: BLASTP 결과를 gene symbols로 변환

### 처리 결과
- **입력**: 46,035개 쌩프 단백질
- **출력**: 44,264개 성공적으로 매핑됨 (96.2% 성공률)
- **최종 결과**: `results/final_gene_symbol_map_FULL.tsv`

---

## 📁 디렉토리 구조

```
/home/laugh/shrimp_code/code/genesymbol/
├── scripts/           # 모든 Python/Bash 스크립트
├── data/              # 원본 입력 데이터 (annotation.gtf, genome.fna)
├── intermediate/      # 중간 산물 파일들
├── results/           # 최종 결과물
├── blast_db/          # BLAST 데이터베이스
├── docs/              # 문서 (README.md, EXECUTION_RESULT.md)
└── .gitignore
```

### 🔑 핵심 파일

| 파일 | 크기 | 설명 |
|------|------|------|
| `scripts/1_extract_loc_to_protein.py` | - | GTF에서 LOC-Protein 매핑 추출 |
| `scripts/extract_proteins_from_gtf.py` | - | Genome + GTF에서 단백질 번역 |
| `scripts/2_extract_proteins.py` | - | FASTA 필터링 및 선택 |
| `scripts/5_map_blast_to_symbol.py` | - | BLASTP 결과를 gene symbol로 변환 |
| `data/annotation.gtf` | 325 MB | 쌩프 유전체 주석 |
| `data/genome.fna` | 4.1 GB | 쌩프 게놈 DNA (.gitignore) |
| `results/final_gene_symbol_map_FULL.tsv` | 2.6 MB | **최종 결과물** |

---

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.x
- Docker (BLASTP 실행용)
- 충분한 RAM (게놈 파일 로드용 8-10GB)

### 전체 파이프라인 실행

```bash
cd /home/laugh/shrimp_code/code/genesymbol/scripts

# Step 1: GTF 파싱
python 1_extract_loc_to_protein.py -o ../intermediate/loc_protein_map.tsv

# Step 2: Protein 번역
python extract_proteins_from_gtf.py -o ../intermediate/proteins.fasta

# Step 3: Query 준비
python 2_extract_proteins.py ../intermediate/proteins.fasta ../intermediate/loc_protein_map.tsv -c 1 -o ../intermediate/shrimp_query.fasta

# Step 4: BLAST DB 생성 (Docker)
docker run --rm -v /home/laugh/shrimp_code/code/genesymbol:/data ncbi/blast:latest \
  makeblastdb -in /data/intermediate/human_ref_proteins.fasta -dbtype prot -out /data/blast_db/human_ref

# Step 5: BLASTP 실행 (Docker)
docker run --rm -v /home/laugh/shrimp_code/code/genesymbol:/data ncbi/blast:latest \
  blastp -db /data/blast_db/human_ref \
         -query /data/intermediate/shrimp_query.fasta \
         -evalue 100 -max_target_seqs 3 -outfmt 6 \
         -out /data/intermediate/blast_results_full.txt

# Step 6: Gene Symbol 매핑
python 5_map_blast_to_symbol.py -o ../results/final_gene_symbol_map_FULL.tsv --min-identity 20 --min-coverage 1
```

### 결과 확인

```bash
# 최종 결과 파일 확인
wc -l ../results/final_gene_symbol_map_FULL.tsv
head -20 ../results/final_gene_symbol_map_FULL.tsv

# Gene symbol별 분포
tail -n +2 ../results/final_gene_symbol_map_FULL.tsv | awk -F'\t' '{print $4}' | sort | uniq -c | sort -nr
```

---

## 📖 상세 가이드

더 자세한 내용은 **`docs/EXECUTION_RESULT.md`**를 참고하세요:

- 각 스크립트의 상세 설명
- 경로 설정 및 자동화 메커니즘
- 출력 파일 형식 설명
- 성능 지표 및 통계
- 재실행 및 커스터마이징 방법

---

## 🔧 각 스크립트 사용법

### 1_extract_loc_to_protein.py

```bash
cd scripts
python 1_extract_loc_to_protein.py                      # 기본 실행 (stdout)
python 1_extract_loc_to_protein.py -o ../intermediate/output.tsv  # 파일 저장
```

**기본값:** `data/annotation.gtf` → `data/`를 기본 경로로 사용

### extract_proteins_from_gtf.py

```bash
cd scripts
python extract_proteins_from_gtf.py                                  # 기본 실행
python extract_proteins_from_gtf.py -o ../intermediate/proteins.fasta # 출력 지정
python extract_proteins_from_gtf.py -v                               # 상세 출력
```

**기본값:** `data/annotation.gtf`, `data/genome.fna` 자동으로 사용

### 2_extract_proteins.py

```bash
cd scripts
python 2_extract_proteins.py <FASTA_FILE> <ID_FILE> -c <COLUMN> -o <OUTPUT>
```

**예시:**
```bash
python 2_extract_proteins.py ../intermediate/proteins.fasta ../intermediate/loc_protein_map.tsv -c 1 -o ../intermediate/shrimp_query.fasta
```

### 5_map_blast_to_symbol.py

```bash
cd scripts
python 5_map_blast_to_symbol.py [옵션]
```

**옵션:**
```bash
-l, --loc-file           LOC → Protein 매핑 (기본값: intermediate/loc_protein_map.tsv)
-b, --blast-file         BLASTP 결과 (기본값: intermediate/blast_results_full.txt)
-a, --annotation-file    Gene symbol 매핑 (기본값: intermediate/human_symbol_map.tsv)
-o, --output             출력 파일 (기본값: stdout)
--min-identity           최소 identity % (기본값: 30.0)
--min-coverage           최소 coverage % (기본값: 30.0)
-v, --verbose            상세 출력
```

**예시:**
```bash
# 기본 설정
python 5_map_blast_to_symbol.py -o ../results/final_gene_symbol_map.tsv

# 더 엄격한 필터링
python 5_map_blast_to_symbol.py -o ../results/filtered.tsv --min-identity 40 --min-coverage 50
```

---

## 💾 출력 파일 형식

### final_gene_symbol_map_FULL.tsv

```
gene_id	protein_id	reference_accession	gene_symbol	identity(%)	coverage(%)	bit_score	evalue
LOC135224517	XP_064077101.1	NP_000002.2	A2M	32.26	9.00	-	-
LOC135194849	XP_064077103.1	NP_000001.3	A1BG	50.00	2.00	-	-
```

**컬럼:**
- `gene_id`: 쌩프 유전자 ID
- `protein_id`: 쌩프 단백질 ID
- `reference_accession`: Human reference accession
- `gene_symbol`: Human gene symbol (A1BG, A2M, A2MP1, AAAS, AAK1)
- `identity(%)`: 아미노산 서열 일치도
- `coverage(%)`: 쿼리 커버리지

---

## ⚙️ 경로 자동화

모든 스크립트는 자동으로 기본 경로를 설정합니다:

```python
# scripts/내부에서 실행할 때
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))     # scripts/
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)                 # 상위 디렉토리
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')              # data/
INTERMEDIATE_DIR = os.path.join(PROJECT_ROOT, 'intermediate')  # intermediate/
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')        # results/
```

따라서 `scripts/` 디렉토리에서 실행하면 모든 경로가 자동으로 올바르게 설정됩니다!

---

## 📊 성능 지표

| 단계 | 처리 시간 | 메모리 | 성공률 |
|------|---------|--------|--------|
| Step 1: GTF 파싱 | <1초 | <100 MB | 100% |
| Step 2: Protein 번역 | ~10분 | ~8-10 GB | 100% |
| Step 3: Query 필터링 | <1초 | <50 MB | 100% |
| Step 5: BLASTP | ~30분 | <500 MB | 97.4% |
| Step 6: Gene mapping | <10초 | <100 MB | 96.2% |

---

## 🔍 문제 해결

### "genome.fna를 찾을 수 없습니다"

`.gitignore`에 등록되어 있습니다. 필요하면 `data/` 폴더에 직접 배치하세요.

### "메모리 부족" 에러

`extract_proteins_from_gtf.py` 실행 시 게놈 파일을 메모리에 로드합니다. 최소 8-10GB RAM이 필요합니다.

### BLASTP 결과가 없습니다

- Docker가 설치되어 있는지 확인: `docker --version`
- 경로가 올바른지 확인: `ls -la ../blast_db/human_ref*`
- 수동으로 BLASTP 실행 시 `-evalue 100`은 매우 관대한 설정입니다.

---

## 📚 참고 자료

- **GTF 형식**: https://www.ensembl.org/info/website/upload/gff.html
- **BLAST 설명서**: https://www.ncbi.nlm.nih.gov/pubmed/20003500
- **유전자 코드**: https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi

---

## 🎯 주요 특징

✅ **완전 자동화** - 경로를 자동으로 설정합니다
✅ **Docker 기반** - 환경 의존성 제거
✅ **문서화** - 모든 스크립트에 help 메시지 포함
✅ **재현 가능** - 모든 중간 산물 보관
✅ **확장 가능** - 다른 reference genome으로 쉽게 확장 가능

---

## 📝 라이선스

이 프로젝트는 연구 목적으로 자유롭게 사용할 수 있습니다.

---

## 📧 문의

이 파이프라인에 대한 질문이나 제안은 프로젝트 문서를 참고하세요.

---

**마지막 업데이트: 2025-11-20**
