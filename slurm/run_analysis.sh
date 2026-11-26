#!/bin/bash
#SBATCH --job-name=agent-trail-study
#SBATCH --output=outputs/slurm_%j.out
#SBATCH --error=outputs/slurm_%j.err
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

set -euo pipefail

mkdir -p outputs
Rscript r/event_study.R data/repo_panel.csv outputs
