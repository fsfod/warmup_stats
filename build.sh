#! /bin/sh

set -e

HERE_DIR=$(dirname $(readlink -f "$0"))
R_INST_DIR=${HERE_DIR}/work/R-inst
PIP_TARGET_DIR=${HERE_DIR}/work/pylibs
mkdir -p ${R_INST_DIR}/lib/R/library

# Install R changepoint package.
echo "install.packages('devtools', lib='${R_INST_DIR}/lib/R/library', repos='http://cran.us.r-project.org')" | R_LIBS_USER=${R_INST_DIR}/lib/R/library/ R --no-save
echo "install.packages('MultinomialCI', lib='${R_INST_DIR}/lib/R/library', repos='http://cran.us.r-project.org')" | R_LIBS_USER=${R_INST_DIR}/lib/R/library/ R --no-save
echo "options(download.file.method = \"wget\"); devtools::install_github('rkillick/changepoint')" | R_LIBS_USER=${R_INST_DIR}/lib/R/library/ R --no-save

# Install rpy2 Python package.
pip install --install-option="--prefix=${PIP_TARGET_DIR}" rpy2==2.8.5
