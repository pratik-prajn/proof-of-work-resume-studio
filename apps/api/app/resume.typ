// Fixed single-column template. User strings are data, never eval() or markup.
#set page(paper: "a4", margin: (x: 16mm, y: 15mm), numbering: none)
#set text(font: ("Noto Sans", "DejaVu Sans"), size: 10.5pt, ligatures: false)
#set par(justify: false, leading: 0.48em)
#set document(title: "Resume", author: ())
#let data = json(bytes(sys.inputs.resume))
#for item in data.blocks {
  if item.kind == "name" {
    block(above: 0pt, below: 7pt, sticky: true)[#text(size: 22pt, weight: "bold", item.text)]
  } else if item.kind == "heading" {
    block(above: 10pt, below: 4pt, sticky: true)[#text(size: 11.5pt, weight: "bold", item.text)]
  } else if item.kind == "bullet" {
    block(above: 0pt, below: 4pt)[#text("- " + item.text)]
  } else {
    block(above: 0pt, below: 3pt)[#text(item.text)]
  }
}
