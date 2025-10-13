import {
  useReactTable,
  getCoreRowModel,
  createColumnHelper,
  getPaginationRowModel,
  getFilteredRowModel,
} from "@tanstack/react-table";
import type { Student } from "./types";
import { useState } from "react";
import { downloadCSV } from "./utils"; // You'll need to create this utility
const columnHelper = createColumnHelper<Student>();

const defaultColumns = [
  columnHelper.accessor("id", {
    header: "ID",
    cell: (info) => (
      <div className="text-sm text-gray-600 font-mono">{info.getValue()}</div>
    ),
    footer: (info) => info.column.id,
  }),
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => (
      <div className="font-medium text-gray-900">{info.getValue()}</div>
    ),
    footer: (info) => info.column.id,
  }),
  columnHelper.accessor("uid", {
    header: "UID",
    cell: (info) => (
      <div className="text-sm text-gray-600 font-mono">{info.getValue()}</div>
    ),
    footer: (info) => info.column.id,
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (info) => {
      const status = info.getValue();
      return (
        <span
          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
            status === true
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {status === true ? "IN" : "OUT"}
        </span>
      );
    },
    footer: (info) => info.column.id,
  }),
  columnHelper.accessor("lastscan", {
    header: "Last Scan",
    filterFn: (row, _columnId, filterValue) => {
      if (!filterValue) return true;

      const timestamp = row.original.lastscan;
      const date = new Date(Number(timestamp) * 1000);

      // Check if filterValue matches any part of the date/time
      const dateString = date.toLocaleDateString();
      const timeString = date.toLocaleTimeString();

      return (
        dateString.toLowerCase().includes(filterValue.toLowerCase()) ||
        timeString.toLowerCase().includes(filterValue.toLowerCase())
      );
    },
    cell: (info) => {
      const timestamp = info.getValue();
      const date = new Date(Number(timestamp) * 1000);
      return (
        <div className="text-sm text-gray-600">
          <div>{date.toLocaleDateString()}</div>
          <div className="text-xs text-gray-500">
            {date.toLocaleTimeString()}
          </div>
        </div>
      );
    },
    footer: (info) => info.column.id,
  }),
  columnHelper.display({
    id: "select",
    header: ({ table }) => (
      <input
        type="checkbox"
        checked={table.getIsAllRowsSelected()}
        ref={(input) => {
          if (input) {
            input.indeterminate = table.getIsSomeRowsSelected();
          }
        }}
        onChange={table.getToggleAllRowsSelectedHandler()}
        className="rounded border-gray-300"
      />
    ),
    cell: ({ row }) => (
      <input
        type="checkbox"
        checked={row.getIsSelected()}
        onChange={row.getToggleSelectedHandler()}
        className="rounded border-gray-300"
      />
    ),
  }),
];

export function StudentTable({ data }: { data: Student[] }) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [rowSelection, setRowSelection] = useState({});

  const table = useReactTable({
    data,
    columns: defaultColumns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    initialState: {
      pagination: {
        pageSize: 5,
      },
    },
    enableSorting: true,
    enableMultiSort: true,
    enableColumnFilters: true,
    enableRowSelection: true,
    globalFilterFn: "includesString",
    onGlobalFilterChange: setGlobalFilter,
    state: {
      globalFilter,
      rowSelection,
    },
    onRowSelectionChange: setRowSelection,
  });

  return (
    <div className="bg-white shadow-lg rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">
            Student Check-in Status
          </h2>
          <input
            type="text"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search students..."
            className="px-3 py-1 text-sm border border-gray-300 rounded-md"
          />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    <div className="flex items-center">
                      {typeof header.column.columnDef.header === "function"
                        ? header.column.columnDef.header(header.getContext())
                        : header.column.columnDef.header}
                      {header.column.getIsSorted() === "asc" && (
                        <span className="ml-1">↑</span>
                      )}
                      {header.column.getIsSorted() === "desc" && (
                        <span className="ml-1">↓</span>
                      )}
                    </div>
                    {header.column.getCanFilter() && (
                      <div className="mt-1">
                        {header.column.getFilterValue() ? (
                          <button
                            onClick={() => header.column.setFilterValue("")}
                            className="text-xs text-gray-500 hover:text-gray-700"
                          >
                            Clear
                          </button>
                        ) : null}
                        <input
                          type="text"
                          value={
                            (header.column.getFilterValue() as string) || ""
                          }
                          onChange={(e) =>
                            header.column.setFilterValue(e.target.value)
                          }
                          placeholder={`Filter ${header.column.id}`}
                          className="text-xs border border-gray-300 rounded px-1 py-0.5"
                        />
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="hover:bg-gray-50 transition-colors duration-150"
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-6 py-4 whitespace-nowrap text-sm"
                  >
                    {typeof cell.column.columnDef.cell === "function"
                      ? cell.column.columnDef.cell(cell.getContext())
                      : String(cell.getValue())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
        <div className="text-sm text-gray-700">
          Showing&nbsp;
          {table.getState().pagination.pageIndex *
            table.getState().pagination.pageSize +
            1}
          &nbsp;to&nbsp;
          {Math.min(
            (table.getState().pagination.pageIndex + 1) *
              table.getState().pagination.pageSize,
            table.getFilteredRowModel().rows.length
          )}
          &nbsp;of {table.getFilteredRowModel().rows.length} results
        </div>

        <div className="flex space-x-2">
          <button
            onClick={() => table.firstPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-1 text-sm rounded-md border border-gray-300 cursor-pointer bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            First
          </button>
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-1 text-sm rounded-md border border-gray-300 cursor-pointer bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          <div className="flex items-center">
            <span className="text-sm text-gray-700 mr-2">Page</span>
            <input
              type="number"
              min={1}
              max={table.getPageCount()}
              value={table.getState().pagination.pageIndex + 1}
              onChange={(e) => {
                const page = e.target.value ? Number(e.target.value) - 1 : 0;
                table.setPageIndex(page);
              }}
              className="w-12 px-2 input py-1 text-sm remove-arrow border border-gray-300 rounded-md text-center"
            />
            <span className="text-sm text-gray-700 ml-2">
              of {table.getPageCount()}
            </span>
          </div>

          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-3 py-1 text-sm rounded-md border cursor-pointer border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
          <button
            onClick={() => table.lastPage()}
            disabled={!table.getCanNextPage()}
            className="px-3 py-1 text-sm rounded-md border cursor-pointer border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Last
          </button>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => table.resetColumnVisibility()}
            className="px-3 py-1 text-sm rounded-md border cursor-pointer border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
          >
            Reset Columns
          </button>
          <button
            onClick={() => table.getColumn("name")?.toggleVisibility()}
            className="px-3 py-1 text-sm rounded-md border cursor-pointer border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
          >
            {table.getColumn("name")?.getIsVisible()
              ? "Hide Name"
              : "Show Name"}
          </button>
          <button
            onClick={() =>
              downloadCSV(
                table.getFilteredRowModel().rows.map((row) => row.original)
              )
            }
            className="px-3 py-1 text-sm rounded-md border cursor-pointer border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
          >
            Export CSV
          </button>
        </div>
      </div>
    </div>
  );
}
