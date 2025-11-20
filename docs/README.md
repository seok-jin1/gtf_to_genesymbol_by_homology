# BLASTP Gene Symbol 매핑 파이프라인

Macrobrachium nipponense 유전자를 Human gene symbols로 매핑하는 완전 자동화 파이프라인

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

#### 현재 결과 (제한된 Reference 사용)
- **입력**: 46,035개 쌩프 단백질
- **출력**: 44,264개 성공적으로 매핑됨 (96.2% 성공률)
- **최종 결과**: `results/final_gene_symbol_map_FULL.tsv`
- ⚠️ **주의**: 현재는 **5개의 Human gene symbols만** 반환
  - A1BG (13,912개 LOC), AAK1 (10,651개), AAAS (7,327개), A2M (6,576개), A2MP1 (5,798개)
  - Reference database가 매우 제한적이기 때문
  - 필터링 기준값: `--min-identity 20 --min-coverage 1` (매우 관대함)

#### 더 나은 결과를 위한 권장사항
더 정확하고 포괄적인 결과를 원하시면 아래 옵션 중 하나를 선택하세요:

**Option A: 필터링 강화 (빠름)**
```bash
cd scripts
# 더 엄격한 기준으로 재분석
python 5_map_blast_to_symbol.py \
  -o ../results/final_gene_symbol_map_STRINGENT.tsv \
  --min-identity 40 --min-coverage 50
```

**Option B: 완전한 Human Proteome 사용 (권장)**
```bash
# Step 1: 완전한 Human reference proteome 다운로드
cd intermediate
wget -q -O human_complete.fasta.gz \
  "ftp://ftp.ncbi.nlm.nih.gov/refseq/H_sapiens/annotation/GRCh38_latest/refseq_identifiers/protein.fasta.gz"
gunzip human_complete.fasta.gz

# Step 2: BLAST Database 생성 (Docker)
docker run --rm -v /home/laugh/shrimp_code/code/genesymbol:/data ncbi/blast:latest \
  makeblastdb -in /data/intermediate/human_complete.fasta -dbtype prot -out /data/blast_db/human_complete

# Step 3: BLASTP 재실행
docker run --rm -v /home/laugh/shrimp_code/code/genesymbol:/data ncbi/blast:latest \
  blastp -db /data/blast_db/human_complete \
         -query /data/intermediate/shrimp_query.fasta \
         -evalue 1e-5 -max_target_seqs 1 -outfmt 6 \
         -out /data/intermediate/blast_results_complete.txt

# Step 4: Gene symbol 매핑 (완전한 데이터 사용)
cd ../scripts
python 5_map_blast_to_symbol.py \
  -b ../intermediate/blast_results_complete.txt \
  -o ../results/final_gene_symbol_map_COMPLETE.tsv \
  --min-identity 30 --min-coverage 30
```

**Option C: Mouse + Drosophila 추가 (멀티종)**
```bash
# Human, Mouse, Drosophila 완전 proteome 병합
cd intermediate
for species in H_sapiens M_musculus D_melanogaster; do
  wget -q -O ${species}.fasta.gz \
    "ftp://ftp.ncbi.nlm.nih.gov/refseq/${species}/annotation/*latest/refseq_identifiers/protein.fasta.gz"
done
gunzip *.fasta.gz
cat H_sapiens.fasta M_musculus.fasta D_melanogaster.fasta > multi_ref.fasta

# BLAST DB 생성 후 동일 단계 진행...
```

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

#### Docker 설치

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS
brew install --cask docker

# 설치 확인
docker --version
```

**Docker 사용 이유:**
- 환경 독립성: BLAST+ 버전 충돌 없음
- 간편한 실행: 복잡한 의존성 관리 불필요
- 재현성: 동일한 실행 환경 보장

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

## 🐳 Docker를 이용한 BLASTP 실행

이 파이프라인은 **Docker**를 사용하여 BLASTP를 실행합니다. 이를 통해 BLAST+ 설치 없이 환경 독립적으로 분석을 수행할 수 있습니다.

### Docker 명령어 설명

#### Step 4: BLAST Database 생성

```bash
docker run --rm \
  -v /home/laugh/shrimp_code/code/genesymbol:/data \
  ncbi/blast:latest \
  makeblastdb \
    -in /data/intermediate/human_ref_proteins.fasta \
    -dbtype prot \
    -out /data/blast_db/human_ref
```

**옵션 설명:**
- `--rm`: 컨테이너 종료 후 자동 삭제
- `-v /path/host:/path/container`: 호스트 디렉토리 마운트
- `ncbi/blast:latest`: NCBI BLAST 공식 Docker 이미지
- `-dbtype prot`: 단백질 database 생성
- `-out`: database 출력 경로

#### Step 5: BLASTP 실행

```bash
docker run --rm \
  -v /home/laugh/shrimp_code/code/genesymbol:/data \
  ncbi/blast:latest \
  blastp \
    -db /data/blast_db/human_ref \
    -query /data/intermediate/shrimp_query.fasta \
    -evalue 100 \
    -max_target_seqs 3 \
    -outfmt 6 \
    -out /data/intermediate/blast_results_full.txt
```

**주요 옵션:**
- `-db`: BLAST database 경로
- `-query`: Query FASTA 파일
- `-evalue`: E-value threshold (낮을수록 엄격)
- `-max_target_seqs`: 반환할 최대 hit 수
- `-outfmt 6`: 탭 구분 텍스트 형식 (컬럼: qseqid, sseqid, pident, length, ...)
- `-out`: 결과 파일 경로

### Docker 트러블슈팅

**Q: Docker 명령어에서 권한 오류 발생**
```bash
# 해결 방법 1: sudo 사용
sudo docker run --rm -v ... ncbi/blast:latest ...

# 해결 방법 2: docker 그룹에 사용자 추가 (재부팅 필요)
sudo usermod -aG docker $USER
```

**Q: Database 파일이 permission denied 에러 발생**
```bash
# Docker가 생성한 파일은 root 소유입니다
# 필요하면 권한 변경:
sudo chown -R $USER:$USER /home/laugh/shrimp_code/code/genesymbol
```

**Q: BLASTP 실행이 느림**
```bash
# CPU 코어 수 조절 가능 (ncbi/blast:latest 이미지는 자동 감지)
# 필요하면 영구적으로 더 많은 컨테이너 리소스 할당:
# Docker Desktop Settings > Resources > CPUs/Memory 조정
```

### Docker vs 로컬 BLAST+ 비교

| 항목 | Docker | 로컬 BLAST+ |
|-----|--------|-----------|
| 설치 | 매우 간단 | 의존성 많음 |
| 버전 관리 | 일관성 보장 | 관리 필요 |
| 재현성 | 완벽함 | 환경 의존 |
| 속도 | 미미한 오버헤드 | 약간 빠름 |
| 크로스플랫폼 | 완벽 | 플랫폼별 차이 |

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

## 📋 결과 해석 및 Reference Database 가이드

### 현재 결과의 특징

현재 파이프라인은 **매우 제한된 Human reference** (5개 단백질)를 사용합니다:
```
A1BG (13,912개 LOC)
AAK1 (10,651개 LOC)
AAAS (7,327개 LOC)
A2M (6,576개 LOC)
A2MP1 (5,798개 LOC)
```

**이는 다음을 의미합니다:**
- ✅ 매우 빠른 분석 (<1분)
- ❌ 제한된 gene symbol 범위
- ❌ 낮은 특이성 (specificity)
- ✅ 높은 민감성 (sensitivity) - 거의 모든 LOC가 매핑됨

### Reference Database 선택 가이드

| 상황 | 추천 선택 | 특징 |
|------|---------|------|
| 빠른 테스트 | 현재 설정 (5개) | 빠르지만 결과 제한적 |
| 정확한 분석 | **Option B (완전 Human)** | 20,000+ 유전자, 가장 권장 |
| 멀티종 비교 | **Option C (Human+Mouse+Fly)** | 포괄적이지만 느림 |
| 매우 엄격한 필터 | Option A + 강한 threshold | 최소 개수의 신뢰할 수 있는 결과 |

### 필터링 기준값 가이드

```
Identity (%) | Coverage (%) | 용도
------------------------------------------
20-30        | 1-10         | 매우 관대 (현재 설정)
30-50        | 20-40        | 중간 정도
50-80        | 40-80        | 엄격 (권장)
>80          | >80          | 매우 엄격
```

### 권장 실행 순서

1. **첫 번째**: 현재 설정 테스트 (5분)
2. **두 번째**: Option B로 완전 분석 (30분)
3. **세 번째**: 필터링 강화 (Option A) 또는 결과 비교

---

## 🔍 문제 해결

### "genome.fna를 찾을 수 없습니다"

`.gitignore`에 등록되어 있습니다. 필요하면 `data/` 폴더에 직접 배치하세요.

### "메모리 부족" 에러

`extract_proteins_from_gtf.py` 실행 시 게놈 파일을 메모리에 로드합니다. 최소 8-10GB RAM이 필요합니다.

### "결과가 5개의 gene symbol만 포함되어 있습니다"

현재 파이프라인이 제한된 reference를 사용하고 있습니다. 위의 "결과 해석" 섹션에서 **Option B (완전한 Human Proteome)**를 따르세요.

### BLASTP 실행 시 오류

- Docker가 설치되어 있는지 확인: `docker --version`
- 경로가 올바른지 확인: `ls -la ../blast_db/human_*`
- 수동으로 BLASTP 실행 시 `-evalue 100`은 매우 관대한 설정입니다.

---

## 📚 참고 자료

- **GTF 형식**: https://www.ensembl.org/info/website/upload/gff.html
- **BLAST 설명서**: https://www.ncbi.nlm.nih.gov/pubmed/20003500
- **유전자 코드**: https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi

---

## 🎯 주요 특징

✅ **완전 자동화** - 경로를 자동으로 설정합니다
✅ **모듈식 스크립트** - 각 단계를 독립적으로 실행 가능
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
