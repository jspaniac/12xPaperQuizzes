import argparse
import csv
import os
from collections import defaultdict, OrderedDict, Counter
import re
import matplotlib.pyplot as plt
import numpy as np


class Student:
    def __init__(self, all):
        self.fname = all[0]
        self.lname = all[1]
        self.email = all[2]
        self.section = all[3]

        self.grades = []
        self.missing = False

    def add_grade(self, grade):
        if (len(self.grades) == 3):
            raise Exception()
        self.grades.append(grade)

    def __repr__(self):
        return f"{self.fname} {self.lname} ({self.section}): {self.grades}"

    def get_grades(self):
        grades = ""
        for grade in self.grades:
            grades += grade
        return grades

    def set_missing(self):
        self.missing = True

    def __eq__(self, other):
        return (self.fname == other.fname and
                self.lname == other.lname and
                self.email == other.email)


def find_cols(file_path):
    problem_to_cols = defaultdict(list)
    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)

        for i in range(len(header)):
            if re.match(r'^[1-3]', header[i]):
                problem_to_cols[int(header[i][:1])].append(i)
    return problem_to_cols


def read_file(section_to_students, section, file_path, thresholds):
    problem_to_cols = find_cols(file_path)
    with open(file_path, 'r') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)

        stud_indices = [
            header.index('First Name'),
            header.index('Last Name'),
            header.index('Email'),
            header.index('Sections'),
        ]

        for row in csv_reader:
            if (section.lower() in row[header.index('Sections')] or
                    row[header.index('Status')] == "Graded"):
                stud = Student([row[index] for index in stud_indices])

                if (row[header.index('Status')] == "Missing"):
                    stud.set_missing()
                    for _ in range(3):
                        stud.add_grade('N')
                else:
                    for prob, indices in problem_to_cols.items():
                        sum = 0
                        for index in indices:
                            sum += float(row[index])

                        if sum >= thresholds[prob - 1][0]:
                            stud.add_grade('E')
                        elif sum >= thresholds[prob - 1][1]:
                            stud.add_grade('S')
                        else:
                            stud.add_grade('N')

                section_to_students[section].append(stud)


def remove_drs(section_to_students):
    for _, studs in section_to_students.items():
        for stud in studs:
            if stud in section_to_students["DRS"]:
                studs.remove(stud)


def load_files(path, thresholds):
    section_to_students = defaultdict(list)
    for root, _, files in os.walk(path):
        for filename in files:
            section = filename.split("_")[2]

            if section != "Version":
                read_file(section_to_students, section,
                          os.path.join(root, filename), thresholds)
    remove_drs(section_to_students)
    return section_to_students


def plot(section_to_students):
    fig = plt.figure(figsize=(10, 6))
    gs = fig.add_gridspec(2, 2)

    plot_distribution(fig.add_subplot(gs[0, :]), section_to_students)
    plot_matrix(fig.add_subplot(gs[1, 0]), section_to_students)
    plot_ns(fig.add_subplot(gs[1, 1]), section_to_students)

    plt.axis('equal')
    plt.tight_layout()
    plt.show()


def plot_ns(axs, section_to_students):
    num_to_count = OrderedDict()
    for i in range(4):
        num_to_count[i] = 0

    for _, studs in section_to_students.items():
        for stud in studs:
            if not stud.missing:
                grades = stud.get_grades()
                num_to_count[sum(1 for grade in grades if grade == "N")] += 1

    axs.pie(num_to_count.values(),
            labels=[f"{key}Ns ({value})" for key, value in num_to_count.items()],
            autopct='%1.1f%%', startangle=140)
    axs.set_aspect('equal')
    axs.set_title("N Counts")


def plot_matrix(axs, section_to_students):
    matrix = np.zeros((3, 3), dtype=int)
    for _, studs in section_to_students.items():
        for stud in studs:
            if not stud.missing:
                grades = stud.get_grades()
                for i in range(len(grades)):
                    matrix[i]["ESN".index(grades[i])] += 1

    im = axs.imshow(matrix, cmap='BuGn')
    _ = axs.figure.colorbar(im, ax=axs)

    axs.set_xticks(np.arange(len(matrix)))
    axs.set_yticks(np.arange(len(matrix)))
    axs.set_xticklabels(['Es', 'Ss', 'Ns'])
    axs.set_yticklabels(['P1', 'P2', 'P3'])

    plt.setp(axs.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            _ = axs.text(j, i, matrix[i, j],
                         ha="center", va="center", color="black")

    axs.set_title("Problem Matrix")


def plot_distribution(axs, section_to_students):
    all_possible = OrderedDict()

    all_possible["None"] = 0
    for n in range(3, -1, -1):
        for e in range(4):
            for s in range(4):
                if e + s + n == 3:
                    all_possible[n * "N" + s * "S" + e * "E"] = 0

    total_studs = 0
    for _, studs in section_to_students.items():
        for stud in studs:
            if (stud.missing):
                all_possible["None"] += 1
            else:
                total_studs += 1
                counts = Counter(tuple(stud.get_grades()))
                all_possible[counts["N"] * "N" + counts["S"] * "S" + counts["E"] * "E"] += 1

    bars = axs.bar(list(all_possible.keys()), list(all_possible.values()),
                   tick_label=list(all_possible.keys()), color='skyblue')

    for bar in bars:
        height = bar.get_height()
        axs.annotate('{} ({}%)'.format(height, round(100 * height / total_studs)),
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3),  # 3 points vertical offset
                     textcoords="offset points",
                     ha='center', va='bottom')

    axs.set_xticklabels(list(all_possible.keys()))
    axs.set_xticks(np.arange(len(all_possible.keys())))

    _, _, ymin, ymax = axs.axis()
    axs.set_ylim(ymin, ymax * 1.20)

    axs.set_xlabel("E/S/N Assignment")
    axs.set_ylabel("Counts")
    axs.set_title("Quiz E/S/N Distribution")


def main():
    parser = argparse.ArgumentParser(
        description="Used for gathering grades from different gradescope versions"
    )

    parser.add_argument(
        '--path', '-p',
        help='Path to gradescope versionset directory',
        required=True
    )
    parser.add_argument(
        '--thresholds', '-t', type=float, nargs='+',
        help='[E S] point thresholds'
    )
    args = parser.parse_args()

    if args.thresholds is None:
        print("No thresholds applied going with standard [E=1.0, S=0.5]")
        args.thresholds = [(1.0, 0.5) for _ in range(3)]
    elif len(args.thresholds) == 2:
        print("Applying provided thresholds to all problems")
        args.thresholds = [(args.thresholds[0], args.thresholds[1])
                           for _ in range(3)]
    elif len(args.thresholds) == 6:
        print("Applying individualized thresholds per problem")
        args.thresholds = [(args.thresholds[i], args.thresholds[i + 1])
                           for i in range(0, len(args.thresholds), 2)]
    else:
        print(f"Error, need no / two / six provided threshold values: {args.thresholds}")
        return
    print(args.thresholds)

    section_to_students = load_files(args.path, args.thresholds)
    plot(section_to_students)


if __name__ == "__main__":
    main()
