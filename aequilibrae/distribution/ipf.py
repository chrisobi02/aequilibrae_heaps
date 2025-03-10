import os
from time import perf_counter
from uuid import uuid4
from datetime import datetime
import importlib.util as iutil
import numpy as np
import yaml
from aequilibrae.matrix import AequilibraeMatrix, AequilibraeData
from aequilibrae.project.data.matrix_record import MatrixRecord
from aequilibrae.context import get_active_project

spec = iutil.find_spec("openmatrix")
has_omx = spec is not None


class Ipf:
    """Iterative proportional fitting procedure

    ::

        import pandas as pd
        from aequilibrae.distribution import Ipf
        from aequilibrae.matrix import AequilibraeMatrix
        from aequilibrae.matrix import AequilibraeData

        matrix = AequilibraeMatrix()

        # Here we can create from OMX or load from an AequilibraE matrix.
        matrix.create_from_omx(path/to/aequilibrae_matrix, path/to/omxfile)

        # The matrix will be operated one (see the note on overwriting), so it does
        # not make sense load an OMX matrix


        source_vectors = pd.read_csv(path/to/CSVs)
        zones = source_vectors.zone.shape[0]

        args = {"entries": zones, "field_names": ["productions", "attractions"],
                "data_types": [np.float64, np.float64], "memory_mode": True}

        vectors = AequilibraEData()
        vectors.create_empty(**args)

        vectors.productions[:] = source_vectors.productions[:]
        vectors.attractions[:] = source_vectors.attractions[:]

        # We assume that the indices would be sorted and that they would match the matrix indices
        vectors.index[:] = source_vectors.zones[:]

        args = {
                "matrix": matrix, "rows": vectors, "row_field": "productions", "columns": vectors,
                "column_field": "attractions", "nan_as_zero": False}

        fratar = Ipf(**args)

         fratar.fit()

        # We can get back to our OMX matrix in the end
        fratar.output.export(path/to_omx/output.omx)
        fratar.output.export(path/to_aem/output.aem)
    """

    def __init__(self, project=None, **kwargs):
        """
        Instantiates the Ipf problem

        Args:
            matrix (:obj:`AequilibraeMatrix`): Seed Matrix

            rows (:obj:`AequilibraeData`): Vector object with data for row totals

            row_field (:obj:`str`): Field name that contains the data for the row totals

            columns (:obj:`AequilibraeData`): Vector object with data for column totals

            column_field (:obj:`str`): Field name that contains the data for the column totals

            project (:obj:`Project`, optional): The Project to connect to. By default, uses the currently active project

            parameters (:obj:`str`, optional): Convergence parameters. Defaults to those in the parameter file

            nan_as_zero (:obj:`bool`, optional): If Nan values should be treated as zero. Defaults to True

        Results:
            output (:obj:`AequilibraeMatrix`): Result Matrix

            report (:obj:`list`): Iteration and convergence report

            error (:obj:`str`): Error description
        """
        self.project = project or get_active_project()
        self.parameters = kwargs.get("parameters", self.__get_parameters("ipf"))

        # Seed matrix
        self.matrix = kwargs.get("matrix", None)  # type: AequilibraeMatrix

        # NaN as zero
        self.nan_as_zero = kwargs.get("nan_as_zero", True)

        # row vector
        self.rows = kwargs.get("rows", None)
        self.row_field = kwargs.get("row_field", None)
        self.output_name = kwargs.get("output", AequilibraeMatrix().random_name())

        # Column vector
        self.columns = kwargs.get("columns", None)
        self.column_field = kwargs.get("column_field", None)

        self.output = AequilibraeMatrix()
        self.error = None
        self.__required_parameters = ["convergence level", "max iterations", "balancing tolerance"]
        self.error_free = True
        self.report = ["  #####    IPF computation    #####  ", ""]
        self.gap = None
        self.procedure_date = ""
        self.procedure_id = ""

    def __check_data(self):
        self.error = None
        self.__check_parameters()

        # check data types
        if not isinstance(self.rows, AequilibraeData):
            raise TypeError("Row vector needs to be an instance of AequilibraeData")

        if not isinstance(self.columns, AequilibraeData):
            raise TypeError("Column vector needs to be an instance of AequilibraeData")

        if not isinstance(self.matrix, AequilibraeMatrix):
            raise TypeError("Seed matrix needs to be an instance of AequilibraeMatrix")

        # Check data type
        if not np.issubdtype(self.matrix.dtype, np.floating):
            raise ValueError("Seed matrix need to be a float type")

        row_data = self.rows.data
        col_data = self.columns.data

        if not np.issubdtype(row_data[self.row_field].dtype, np.floating):
            raise ValueError("production/rows vector must be a float type")

        if not np.issubdtype(col_data[self.column_field].dtype, np.floating):
            raise ValueError("Attraction/columns vector must be a float type")

        # Check data dimensions
        if not np.array_equal(self.rows.index, self.columns.index):
            raise ValueError("Indices from row vector do not match those from column vector")

        if not np.array_equal(self.matrix.index, self.columns.index):
            raise ValueError("Indices from vectors do not match those from seed matrix")

        # Check if matrix was set for computation
        if self.matrix.matrix_view is None:
            raise ValueError("Matrix needs to be set for computation")
        else:
            if len(self.matrix.matrix_view.shape[:]) > 2:
                raise ValueError("Matrix' computational view needs to be set for a single matrix core")

        if self.error is None:
            # check balancing:
            sum_rows = np.nansum(row_data[self.row_field])
            sum_cols = np.nansum(col_data[self.column_field])
            if abs(sum_rows - sum_cols) > self.parameters["balancing tolerance"]:
                self.error = "Vectors are not balanced"
            else:
                # guarantees that they are precisely balanced
                col_data[self.column_field][:] = col_data[self.column_field][:] * (sum_rows / sum_cols)

        if self.error is not None:
            self.error_free = False

    def __check_parameters(self):
        for i in self.__required_parameters:
            if i not in self.parameters:
                self.error = "Parameters error. It needs to be a dictionary with the following keys: "
                for t in self.__required_parameters:
                    self.error = self.error + t + ", "
        if self.error:
            raise ValueError(self.error)

    def fit(self):
        """Runs the IPF instance problem to adjust the matrix

        Resulting matrix is the *output* class member
        """
        self.procedure_id = uuid4().hex
        self.procedure_date = str(datetime.today())
        t = perf_counter()
        self.__check_data()
        if self.error_free:
            max_iter = self.parameters["max iterations"]
            conv_criteria = self.parameters["convergence level"]

            if self.matrix.is_omx():
                self.output = AequilibraeMatrix()
                self.output.create_from_omx(
                    self.output.random_name(), self.matrix.file_path, cores=self.matrix.view_names
                )
                self.output.computational_view()
            else:
                self.output = self.matrix.copy(self.output_name, memory_only=True)
            if self.nan_as_zero:
                self.output.matrix_view[:, :] = np.nan_to_num(self.output.matrix_view)[:, :]

            rows = self.rows.data[self.row_field]
            columns = self.columns.data[self.column_field]
            tot_matrix = np.nansum(self.output.matrix_view[:, :])

            # Reporting
            self.report.append("Target convergence criteria: " + str(conv_criteria))
            self.report.append("Maximum iterations: " + str(max_iter))
            self.report.append("")
            self.report.append("Rows:" + str(self.rows.entries))
            self.report.append("Columns: " + str(self.columns.entries))

            self.report.append("Total of seed matrix: " + "{:28,.4f}".format(float(tot_matrix)))
            self.report.append("Total of target vectors: " + "{:25,.4f}".format(float(np.nansum(rows))))
            self.report.append("")
            self.report.append("Iteration,   Convergence")
            self.gap = conv_criteria + 1

            iter = 0
            while self.gap > conv_criteria and iter < max_iter:
                iter += 1
                # computes factors for zones
                marg_rows = self.__tot_rows(self.output.matrix_view[:, :])
                row_factor = self.__factor(marg_rows, rows)
                # applies factor
                self.output.matrix_view[:, :] = np.transpose(
                    np.transpose(self.output.matrix_view[:, :]) * np.transpose(row_factor)
                )[:, :]

                # computes factors for columns
                marg_cols = self.__tot_columns(self.output.matrix_view[:, :])
                column_factor = self.__factor(marg_cols, columns)

                # applies factor
                self.output.matrix_view[:, :] = self.output.matrix_view[:, :] * column_factor

                # increments iterarions and computes errors
                self.gap = max(
                    abs(1 - np.min(row_factor)),
                    abs(np.max(row_factor) - 1),
                    abs(1 - np.min(column_factor)),
                    abs(np.max(column_factor) - 1),
                )

                self.report.append(str(iter) + "   ,   " + str("{:4,.10f}".format(float(np.nansum(self.gap)))))

            self.report.append("")
            self.report.append("Running time: " + str("{:4,.3f}".format(perf_counter() - t)) + "s")

    def save_to_project(self, name: str, file_name: str) -> MatrixRecord:
        """Saves the matrix output to the project file

        Args:
            name (:obj:`str`): Name of the desired matrix record
            file_name (:obj:`str`): Name for the matrix file name. AEM and OMX supported
        """

        mats = self.project.matrices
        record = mats.new_record(name, file_name, self.output)
        record.procedure_id = self.procedure_id
        record.timestamp = self.procedure_date
        record.procedure = "Iterative Proportional fitting"
        record.save()
        return record

    def __tot_rows(self, matrix):
        return np.nansum(matrix, axis=1)

    def __tot_columns(self, matrix):
        return np.nansum(matrix, axis=0)

    def __factor(self, marginals, targets):
        f = np.divide(targets, marginals)  # We compute the factors
        f[f == np.NINF] = 1  # And treat the errors
        return f

    def __get_parameters(self, model):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(path + "/parameters.yml", "r") as yml:
            path = yaml.safe_load(yml)
        return path["distribution"][model]
