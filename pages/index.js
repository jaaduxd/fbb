import { useEffect, useState } from "react";

export default function Home() {
  const [pages, setPages] = useState([]);
  const [selectedPages, setSelectedPages] = useState([]);
  const [caption, setCaption] = useState("");
  const [media, setMedia] = useState(null);
  const [msg, setMsg] = useState("");
  const [isUploading, setUploading] = useState(false);

  useEffect(() => {
    fetch("/api/get_pages")
      .then((r) => r.json())
      .then(setPages)
      .catch(() => setMsg("FB pages fetch failed"));
  }, []);

  function togglePage(page_id) {
    setSelectedPages((prev) =>
      prev.includes(page_id)
        ? prev.filter((id) => id !== page_id)
        : [...prev, page_id]
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!media || !selectedPages.length) {
      setMsg("Select at least one page and one media file");
      return;
    }

    setUploading(true);
    setMsg("Uploading...");

    const form = new FormData();
    form.append("media", media);
    form.append("pages", JSON.stringify(selectedPages));
    form.append("caption", caption);

    const resp = await fetch("/api/post_media", {
      method: "POST",
      body: form,
    });
    const data = await resp.json();
    setUploading(false);
    if (resp.ok) setMsg("Done: " + JSON.stringify(data));
    else setMsg("ERROR: " + JSON.stringify(data));
  }

  return (
    <div style={{maxWidth:600,margin:"2em auto",padding:"2em",border:"1px solid #eee",borderRadius:10}}>
      <h2>FB Multi-Page Poster</h2>
      <form onSubmit={handleSubmit} encType="multipart/form-data">
        <div>
          <b>Step 1: Select Pages</b><br/>
          {pages.map((p) => (
            <label key={p.id} style={{ display: "block" }}>
              <input
                type="checkbox"
                checked={selectedPages.includes(p.id)}
                onChange={() => togglePage(p.id)}
              />
              {p.name}
            </label>
          ))}
        </div>

        <div style={{margin:"1em 0"}}>
          <b>Step 2: Select Media File</b><br/>
          <input type="file" accept="image/*,video/*" onChange={e=>setMedia(e.target.files[0])}/>
        </div>

        <div>
          <b>Step 3: Caption for All</b><br/>
          <textarea value={caption} onChange={e=>setCaption(e.target.value)} rows={3} cols={45}/>
        </div>

        <button type="submit" disabled={isUploading} style={{marginTop:"1em"}}>
          {isUploading ? "Posting..." : "Publish"}
        </button>
      </form>
      <div style={{marginTop:"1em",color:"red"}}>{msg}</div>
    </div>
  );
}

