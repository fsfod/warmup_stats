import math

from collections import Counter, OrderedDict
from warmup.latex import end_document, end_table, escape, format_median_error
from warmup.latex import get_latex_symbol_map, preamble, STYLE_SYMBOLS
from warmup.statistics import bootstrap_confidence_interval


TITLE = 'Summary of benchmark classifications'
TABLE_FORMAT = 'll@{\hspace{0cm}}lp{5pt}r@{\hspace{0cm}}r@{\hspace{0cm}}r@{\hspace{0cm}}l@{\hspace{.3cm}}lp{5pt}r@{\hspace{0cm}}r@{\hspace{0cm}}r'
TABLE_HEADINGS_START1 = '\\multicolumn{1}{c}{\\multirow{2}{*}{}}&'
TABLE_HEADINGS_START2 = '&'
TABLE_HEADINGS1 = '&&\\multicolumn{1}{c}{} &\\multicolumn{1}{c}{Steady}&\\multicolumn{1}{c}{Steady}&\\multicolumn{1}{c}{Steady}'
TABLE_HEADINGS2 = '&&\\multicolumn{1}{c}{Class.} &\\multicolumn{1}{c}{iter (\#)} &\\multicolumn{1}{c}{iter (s)}&\\multicolumn{1}{c}{perf (s)}'

BLANK_CELL = '\\begin{minipage}[c][\\blankheight]{0pt}\\end{minipage}'


def collect_summary_statistics(data_dictionaries, half_bound, delta, steady_state):
    summary_data = dict()
    # Although the caller can pass >1 json file, there should never be two
    # different machines.
    assert len(data_dictionaries) == 1
    machine = data_dictionaries.keys()[0]
    summary_data = { machine: dict() }
    # Parse data dictionaries.
    keys = sorted(data_dictionaries[machine]['wallclock_times'].keys())
    for key in sorted(keys):
        wallclock_times = data_dictionaries[machine]['wallclock_times'][key]
        if len(wallclock_times) == 0:
            print ('WARNING: Skipping: %s from %s (no executions)' %
                   (key, machine))
        elif len(wallclock_times[0]) == 0:
            print('WARNING: Skipping: %s from %s (benchmark crashed)' %
                  (key, machine))
        else:
            bench, vm, variant = key.split(':')
            if vm not in summary_data[machine].keys():
                summary_data[machine][vm] = list()
            # Get information for all p_execs of this key.
            categories = list()
            steady_state_means = list()
            steady_iters = list()
            time_to_steadys = list()
            n_pexecs = len(data_dictionaries[machine]['wallclock_times'][key])
            # Lists of changepoints, outliers and segment means for each process execution.
            changepoints, outliers, segments = list(), list(), list()
            for p_exec in xrange(n_pexecs):
                changepoints.append(data_dictionaries[machine]['changepoints'][key][p_exec])
                segments.append(data_dictionaries[machine]['changepoint_means'][key][p_exec])
                outliers.append(data_dictionaries[machine]['all_outliers'][key][p_exec])
                categories.append(data_dictionaries[machine]['classifications'][key][p_exec])
                # Next we calculate the iteration at which a steady state was
                # reached, it's average segment mean and the time to reach a
                # steady state. However, the last segment may be equivalent to
                # its adjacent segments, so we first need to know which segments
                # are steady-state segments.
                first_steady_segment = len(data_dictionaries[machine]['changepoint_means'][key][p_exec]) - 1
                num_steady_segments = 1
                last_segment_mean = data_dictionaries[machine]['changepoint_means'][key][p_exec][-1]
                lower_bound = min(last_segment_mean * (1.0 - half_bound), last_segment_mean - delta)
                upper_bound = max(last_segment_mean * (1.0 + half_bound), last_segment_mean + delta)
                for index in xrange(len(data_dictionaries[machine]['changepoint_means'][key][p_exec]) - 2, -1, -1):
                    current_segment_mean = data_dictionaries[machine]['changepoint_means'][key][p_exec][index]
                    if current_segment_mean >= lower_bound and current_segment_mean <= upper_bound:
                        first_steady_segment -= 1
                        num_steady_segments += 1
                    else:
                        break
                steady_state_mean = (math.fsum(data_dictionaries[machine]['changepoint_means'][key][p_exec][first_steady_segment:])
                                     / float(num_steady_segments))
                steady_state_means.append(steady_state_mean)
                # Not all process execs have changepoints. However, all
                # p_execs will have one or more segment mean.
                if data_dictionaries[machine]['changepoints'][key][p_exec]:
                    steady_iter = data_dictionaries[machine]['changepoints'][key][p_exec][first_steady_segment - 1]
                    steady_iters.append(steady_iter)
                    to_steady = 0.0
                    for index in xrange(steady_iter):
                        to_steady += data_dictionaries[machine]['wallclock_times'][key][p_exec][index]
                    time_to_steadys.append(to_steady)
                else:  # Flat execution, no changepoints.
                    time_to_steadys.append(0.0)
            # Get overall and detailed categories.
            categories_set = set(categories)
            if len(categories_set) == 1:  # NB some benchmarks may have errored.
                reported_category = categories[0]
            elif categories_set == set(['flat', 'warmup']):
                reported_category = 'good inconsistent'
            else:  # Bad inconsistent.
                reported_category = 'bad inconsistent'
            cat_counts = dict()
            for category, occurences in Counter(categories).most_common():
                cat_counts[category] = occurences
            for category in ['flat', 'warmup', 'slowdown', 'no steady state']:
                if category not in cat_counts:
                    cat_counts[category] = 0
            # Average information for all process executions.
            if cat_counts['no steady state'] > 0:
                median_time, error_time = None, None
                median_iter, error_iter = None, None
                median_time_to_steady, error_time_to_steady = None, None
            else:
                median_time, error_time = bootstrap_confidence_interval(steady_state_means)
                if steady_iters:
                    median_iter, error_iter = bootstrap_confidence_interval(steady_iters)
                    median_iter = int(math.ceil(median_iter))
                    error_iter = int(math.ceil(error_iter))
                    median_time_to_steady, error_time_to_steady = bootstrap_confidence_interval(time_to_steadys)
                else:  # No changepoints in any process executions.
                    median_iter, error_iter = 0, 0
                    median_time_to_steady, error_time_to_steady = None, None
            # Add summary for this benchmark.
            current_benchmark = dict()
            current_benchmark['benchmark_name'] = bench
            current_benchmark['classification'] = reported_category
            current_benchmark['detailed_classification'] = cat_counts
            current_benchmark['steady_state_iteration'] = median_iter
            current_benchmark['steady_state_iteration_confidence_interval'] = error_iter
            current_benchmark['steady_state_time_to_reach_secs'] = median_time_to_steady
            current_benchmark['steady_state_time_to_reach_secs_confidence_interval'] = error_time_to_steady
            current_benchmark['steady_state_time'] = median_time
            current_benchmark['steady_state_time_confidence_interval'] = error_time
            pexecs = list()
            for index in xrange(n_pexecs):
                pexecs.append({'index':index, 'classification':categories[index],
                              'outliers':outliers[index], 'changepoints':changepoints[index],
                              'segment_means':segments[index]})
            current_benchmark['process_executons'] = pexecs
            summary_data[machine][vm].append(current_benchmark)
    return summary_data


def convert_to_latex(summary_data, half_bound, delta, steady_state):
    assert len(summary_data.keys()) == 1, 'Cannot summarise data from more than one machine.'
    machine = summary_data.keys()[0]
    benchmark_names = set()
    latex_summary = dict()
    for vm in summary_data[machine]:
        latex_summary[vm] = dict()
        for bmark in summary_data[machine][vm]:
            benchmark_names.add(bmark['benchmark_name'])
            if bmark['classification'] == 'bad inconsistent':
                reported_category = STYLE_SYMBOLS['bad inconsistent']
                cats_sorted = OrderedDict(sorted(bmark['detailed_classification'].items(),
                                                 key=lambda x: x[1], reverse=True))
                cat_counts = list()
                for category in cats_sorted:
                    if cats_sorted[category] == 0:
                        continue
                    cat_counts.append('$%d$%s' % (cats_sorted[category], STYLE_SYMBOLS[category]))
                reported_category += ' \\scriptsize(%s)' % ', '.join(cat_counts)
            elif bmark['classification'] == 'good inconsistent':
                reported_category = STYLE_SYMBOLS['good inconsistent']
                cats_sorted = OrderedDict(sorted(bmark['detailed_classification'].items(),
                                                 key=lambda x: x[1], reverse=True))
                cat_counts = list()
                for category in cats_sorted:
                    if cats_sorted[category] == 0:
                        continue
                    cat_counts.append('$%d$%s' % (cats_sorted[category], STYLE_SYMBOLS[category]))
                reported_category += ' \\scriptsize(%s)' % ', '.join(cat_counts)
            elif (sum(bmark['detailed_classification'].values()) ==
                  bmark['detailed_classification'][bmark['classification']]):
                # Consistent benchmark with no errors.
                reported_category = STYLE_SYMBOLS[bmark['classification']]
            else:  # No inconsistencies, but some process executions errored.
                reported_category = ' %s\\scriptsize{($%d$)}' % \
                                    (STYLE_SYMBOLS[bmark['classification']],
                                     bmark['detailed_classification'][bmark['classification']])
            if bmark['steady_state_iteration'] is not None:
                mean_steady_iter = format_median_error(bmark['steady_state_iteration'],
                                                       bmark['steady_state_iteration_confidence_interval'],
                                                       as_integer=True)
            else:
                mean_steady_iter = ''
            if bmark['steady_state_time'] is not None:
                mean_steady = format_median_error(bmark['steady_state_time'],
                                                  bmark['steady_state_time_confidence_interval'])
            else:
                mean_steady = ''
            if bmark['steady_state_time_to_reach_secs'] is not None:
                time_to_steady = format_median_error(bmark['steady_state_time_to_reach_secs'],
                                                     bmark['steady_state_time_to_reach_secs_confidence_interval'],
                                                     brief=True)
            else:
                time_to_steady = ''
            latex_summary[vm][bmark['benchmark_name']] = {'style': reported_category,
                'last_cpt': mean_steady_iter, 'last_mean': mean_steady,
                'time_to_steady_state':time_to_steady}
    return machine, list(sorted(benchmark_names)), latex_summary


def write_latex_table(machine, all_benchs, summary, tex_file, num_splits, with_preamble=False):
    """Write a tex table to disk"""

    num_benchmarks = len(all_benchs)
    all_vms = sorted(summary.keys())
    num_vms = len(summary)

    # decide how to lay out the splits
    num_vms_rounded = int(math.ceil(num_vms / float(num_splits)) * num_splits)
    vms_per_split = int(num_vms_rounded / float(num_splits))
    splits = [[] for x in xrange(num_splits)]
    vm_num = 0
    split_idx = 0
    for vm_idx in xrange(num_vms_rounded):
        if vm_idx < len(all_vms):
            vm = all_vms[vm_idx]
        else:
            vm = None
        splits[split_idx].append(vm)
        vm_num += 1
        if vm_num % vms_per_split == 0:
            split_idx += 1

    with open(tex_file, 'w') as fp:
        if with_preamble:
            fp.write(preamble(TITLE))
            fp.write('\centering %s' % get_latex_symbol_map())
            fp.write('\n\n\n')
            fp.write('\\begin{table*}[t]\n')
            fp.write('\\centering\n')
        # emit table header
        heads1 = TABLE_HEADINGS_START1 + '&'.join([TABLE_HEADINGS1] * num_splits)
        heads2 = TABLE_HEADINGS_START2 + '&'.join([TABLE_HEADINGS2] * num_splits)
        heads = '%s\\\\%s' % (heads1, heads2)
        fp.write(\
"""
{
\\begin{tabular}{%s}
\\toprule
%s \\\\
\\midrule
""" % (TABLE_FORMAT, heads))

        split_row_idx = 0
        for row_vms in zip(*splits):
            bench_idx = 0
            for bench in sorted(all_benchs):
                row = []
                for vm in row_vms:
                    if vm is None:
                        continue # no more results
                    try:
                        this_summary = summary[vm][bench]
                    except KeyError:
                        last_cpt = BLANK_CELL
                        time_steady = BLANK_CELL
                        last_mean = BLANK_CELL
                        classification = ''
                    else:
                        classification = this_summary['style']
                        last_cpt = this_summary['last_cpt']
                        time_steady = this_summary['time_to_steady_state']
                        last_mean = this_summary['last_mean']

                        classification = '\\multicolumn{1}{l}{%s}' % classification
                        if classification == STYLE_SYMBOLS['flat']:
                            last_cpt = BLANK_CELL
                            time_steady = BLANK_CELL
                    if last_cpt == '':
                        last_cpt = BLANK_CELL
                    if time_steady == '':
                        time_steady = BLANK_CELL
                    if last_mean == '':
                        last_mean = BLANK_CELL

                    if bench_idx == 0:
                        if num_benchmarks == 10:
                            fudge = 4
                        elif num_benchmarks == 12:
                            fudge = 5
                        else:
                            fudge = 0
                        vm_cell = '\\multirow{%s}{*}{\\rotatebox[origin=c]{90}{%s}}' \
                            % (num_benchmarks + fudge, vm)
                    else:
                        vm_cell = ''
                    row_add = [BLANK_CELL, vm_cell, classification, last_cpt,
                               time_steady, last_mean]
                    if not row:  # first bench in this row, needs the vm column
                        row.insert(0, escape(bench))
                    row.extend(row_add)
                    vm_idx += 1
                fp.write('&'.join(row))
                # Only -ve space row if not next to a midrule
                if bench_idx < num_vms - 1:
                    fp.write('\\\\[-3pt] \n')
                else:
                    fp.write('\\\\ \n')
                bench_idx += 1
            if split_row_idx < vms_per_split - 1:
                fp.write('\midrule\n')
            split_row_idx += 1
        fp.write(end_table())
        if with_preamble:
            fp.write('\\end{table*}\n')
            fp.write(end_document())