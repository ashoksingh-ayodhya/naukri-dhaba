interface Props {
  content: string;
}

export default function MarkdownContent({ content }: Props) {
  if (!content?.trim()) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let listBuffer: string[] = [];
  let orderedBuffer: string[] = [];
  let key = 0;

  function flushLists() {
    if (listBuffer.length) {
      elements.push(
        <ul key={key++} className="list-disc pl-5 space-y-1 text-sm text-slate-700 mb-3">
          {listBuffer.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: renderInline(item) }} />)}
        </ul>
      );
      listBuffer = [];
    }
    if (orderedBuffer.length) {
      elements.push(
        <ol key={key++} className="list-decimal pl-5 space-y-1 text-sm text-slate-700 mb-3">
          {orderedBuffer.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: renderInline(item) }} />)}
        </ol>
      );
      orderedBuffer = [];
    }
  }

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) { flushLists(); continue; }

    if (trimmed.startsWith("## ")) {
      flushLists();
      elements.push(<h2 key={key++} className="font-heading font-bold text-lg text-slate-900 mt-4 mb-2">{trimmed.slice(3)}</h2>);
    } else if (trimmed.startsWith("# ")) {
      flushLists();
      elements.push(<h1 key={key++} className="font-heading font-bold text-xl text-slate-900 mt-4 mb-2">{trimmed.slice(2)}</h1>);
    } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (orderedBuffer.length) { flushLists(); }
      listBuffer.push(trimmed.slice(2));
    } else if (/^\d+\.\s/.test(trimmed)) {
      if (listBuffer.length) { flushLists(); }
      orderedBuffer.push(trimmed.replace(/^\d+\.\s/, ""));
    } else {
      flushLists();
      elements.push(<p key={key++} className="text-sm text-slate-700 leading-relaxed mb-3" dangerouslySetInnerHTML={{ __html: renderInline(trimmed) }} />);
    }
  }
  flushLists();

  return <div className="prose-content">{elements}</div>;
}

function renderInline(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code class="bg-slate-100 px-1 rounded text-xs">$1</code>');
}
