
from aequilibrae.project import Project
import pandas as pd
import warnings
import timeit
from argparse import ArgumentParser
from time import sleep

def aequilibrae_compute_skim(graph, cores):
    from aequilibrae.paths import NetworkSkimming
    # And run the skimming
    skm = NetworkSkimming(graph)
    skm.results.set_cores(cores)
    skm.execute()
    return skm.results.skims


def aequilibrae_init(proj_path: str, cost: str, cores: int = 0):
    """
    Prepare the graph for skimming the network for `cost`
    """
    proj = Project()
    proj.open(proj_path)
    # curr.execute("select st_x(geometry), st_y(geometry) from nodes")
    # geo = np.array(curr.fetchall())

    proj.network.build_graphs([cost])
    graph = proj.network.graphs["c"]
    graph.prepare_graph(graph.centroids)
    # let's say we want to minimize the cost
    graph.set_graph(cost)

    # And will skim the cost while we are at it
    graph.set_skimming(cost)

    # And we will allow paths to be compute going through other centroids/centroid connectors
    # required for the Sioux Falls network, as all nodes are centroids
    # BE CAREFUL WITH THIS SETTING
    graph.set_blocked_centroid_flows(False)
    return graph

def aequilibrae_testing(graph, cost: str, iters: int = 2, repeats: int = 5):
    graph = aequilibrae_init(graph, cost)
    t = timeit.Timer(lambda: aequilibrae_compute_skim(graph))
    times = t.repeat(repeat=repeats, number=iters)
    return times

projects = [r"C:\Users\61435\Desktop\Aequilibrae examples\models\chicago_sketch"]#, r"C:\Users\61435\Downloads\LongAn\LongAn"]
iters = 1
repeats = 5

def bench():
    info = []

    parser = ArgumentParser()
    parser.add_argument("--name", dest="name", default="name")
    parser.add_argument("--out", dest="path", default= r"C:\Users\61435\Desktop\aequilibrae\aequilibrae\paths\heaps\utils/")
    parser.add_argument("--graphs", dest="graphs", default=[])
    args = vars(parser.parse_args())
    print("benching: " + args["name"])
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        # pandas future warnings are really annoying FIXME

        for proj in projects:
            print("initialising: ", proj.split("\\")[-1])
            graph = aequilibrae_init(proj, "distance")

            print("skimming")
            t = timeit.Timer(lambda: aequilibrae_compute_skim(graph, 1))

            df = pd.DataFrame({"runtime": [x / iters for x in t.repeat(repeat=repeats, number=iters)]})
            df["heap"] = args["name"]
            df["project_name"] = proj.split("\\")[-1]
            info.append(df)
        summary = pd.concat(info)
        print(summary)
        summary.to_csv(args["path"]+ args["name"]+".csv")


if __name__ == "__main__":
    bench()
