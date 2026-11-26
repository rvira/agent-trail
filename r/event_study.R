# AgentTrail: Descriptive Statistics & Event Study Analysis
# Evaluates changes in repository activity around AI coding agent adoption.

args <- commandArgs(trailingOnly = TRUE)
input_path <- if (length(args) >= 1) args[1] else "data/repo_panel.csv"
output_dir <- if (length(args) >= 2) args[2] else "outputs"

if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

if (!file.exists(input_path)) {
  stop(sprintf("Input panel file not found: %s", input_path))
}

panel <- read.csv(input_path, stringsAsFactors = FALSE)

# Expected columns: repo_id, week_rel_adoption, commits, prs_merged, releases, adopted
summary_stats <- aggregate(
  cbind(commits, prs_merged, releases) ~ adopted,
  data = panel,
  FUN = function(x) c(mean = mean(x, na.rm = TRUE), sd = sd(x, na.rm = TRUE), n = length(x))
)

write.csv(
  do.call(data.frame, summary_stats),
  file.path(output_dir, "descriptive_stats.csv"),
  row.names = FALSE
)

# Simple pre/post event-study regression around adoption week (week_rel_adoption >= 0)
panel$post <- as.integer(panel$week_rel_adoption >= 0)
model <- lm(commits ~ post * adopted + factor(week_rel_adoption), data = panel)

sink(file.path(output_dir, "event_study_summary.txt"))
print(summary(model))
sink()
