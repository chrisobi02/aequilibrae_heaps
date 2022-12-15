import os
import subprocess
import shutil
from Cython.Build import cythonize
from setuptools import setup
from shutil import copyfile
from os.path import join, isfile
import warnings

from utils.validation import validate as val
import timeit
import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

os.chdir(r"C:\Users\61435\Desktop\aequilibrae")
num_heaps = 4
path_to_heaps = "aequilibrae/paths/heaps"
relative_heap_path = "heaps/"
#heap_paths = [\heap" + str(i) + r"\basic_path_finding.pyx" for i in range(1, num_heaps+1)]
heap_names = ["binary", "four", "k", "fibonacci"]
projects = [r"C:\Users\61435\Desktop\Aequilibrae examples\models\chicago_sketch", r"C:\Users\61435\Downloads\LongAn\LongAn"]
proj_name = ["Chicago", "LongAn"]
iters = 1
repeats = 3
heaps = [f for f in os.listdir(path_to_heaps) if isfile(join(path_to_heaps, f)) and f.endswith('.pyx')]
min_elem_checker = {
    "fibonacci.pyx": "heap.min_node"

}

def bench():
    import utils.aeq_testing as at
    info = []
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        # pandas future warnings are really annoying FIXME
        cache = {}
        for proj in projects:
            print("caching: ", proj)
            cache[proj] = at.aequilibrae_init(proj, "distance")
            shutil.copyfile(path_to_heaps + "/utils/basic_path_finding.pyx", "aequilibrae/paths/basic_path_finding.pyx")
            graph = cache.get(proj)
            print("skimming")
            t = timeit.Timer(lambda: at.aequilibrae_compute_skim(graph, 1))
            print("benching " + "original pathfinding")
            df = pd.DataFrame({"runtime": [x / iters for x in t.repeat(repeat=repeats, number=iters)]})
            df["heap"] = "original pathfinding"
            df["project_name"] = proj.split("\\")[-1]
            info.append(df)

        for i, path in enumerate(heaps):
            # render specific implementation
            print("rendering: " + path)
            render_template(relative_heap_path+path)
            for j, proj in enumerate(projects):
                print("initialising project ", proj.split("\\")[-1])
                #run a project
                graph = cache.get(proj)
                #Compile at this step

                t = timeit.Timer(lambda: at.aequilibrae_compute_skim(graph, 1))
                print("benching "+path.split(".")[0])
                df = pd.DataFrame({"runtime": [x / iters for x in t.repeat(repeat=repeats, number=iters)]})
                df["heap"] = path.split(".")[0]
                df["project_name"] = proj.split("\\")[-1]
                info.append(df)
        summary = pd.concat(info).groupby(["project_name", "heap"]).agg(
            average=("runtime", "mean"), min=("runtime", "min"), max=("runtime", "max")
        )
        print(summary)
            #get results for time

            #Move pathfinding back into its folder and make a graph

def validate(heap_paths: list):
    import utils.aeq_testing as at
    info = []
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        cache = {}
        for proj in projects:
            print("caching: ", proj)
            cache[proj] = at.aequilibrae_init(proj, "distance")
        # pandas future warnings are really annoying FIXME

        for i, path in enumerate(heap_paths):
            # Move heap_path into paths
            print("rendering: " + path)
            render_template(relative_heap_path + path)
            for j, proj in enumerate(projects):
                print("initialising project ", proj.split("\\")[-1])
                # run a project
                graph = cache.get(proj)
                print("running skim")
                info.append(at.aequilibrae_compute_skim(graph, 0).get_matrix("distance"))
        #Validating skims
        for i, skm1 in enumerate(info):
            for j, skm2 in enumerate(info):
                if i != j:
                    print(skm1)
                    print(skm2)
                    if val(skm1, skm2) is not True:
                        raise Exception("All is not good in the hood between skim indices: ", str(i),str(j))
        print("Skims agree, the k-dary heaps reign supremesn")

def copy():
    shutil.copyfile(path_to_heaps + "/utils/basic_path_finding.pyx", "aequilibrae/paths/basic_path_finding.pyx")

def render_template(heap_path: str):
    heap_type = heap_path.split("/")[-1]
    env = Environment(loader=PackageLoader("benchmark", "templates"))
    template = env.get_template("pathfinding_template.html.jinja")
    out = template.render(HEAP_PATH=f"'{heap_path}'", 
                          MIN_ELEM=min_elem_checker.get(heap_type, "heap.next_available_index != 0"),
                          PARAM="include 'parameters.pxi'" if min_elem_checker.get(heap_type, None) is None else "")
    with open('aequilibrae/paths/basic_path_finding.pyx', 'w') as f:
        f.write(out)

if __name__ == "__main__":
    #validate(heaps)
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        for heap in heaps[0:1]:
            print("rendering ", heap)
            render_template(relative_heap_path + heap)
            print("compiling")
            subprocess.run(["python", "setup_Assignment.py", "build_ext", "--inplace"],
                           cwd=r"C:\Users\61435\Desktop\aequilibrae\aequilibrae\paths"
                           )
            print("compilation complete")
            subprocess.run(["python", path_to_heaps + "/utils/aeq_testing.py", "--name", heap.split(".")[0]],
                            cwd=r"C:\Users\61435\Desktop\aequilibrae\aequilibrae\paths")
        print("made it this far")