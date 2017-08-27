var textareaMarkdown = $("textarea.markdown");

if (textareaMarkdown.length > 0) {
  textareaMarkdown.each(function () {
    new SimpleMDE({
      element: $(this)[0],
      previewRender: _.debounce(function (plainText, preview) {
        $.post("/api/markdown/", {
          csrfmiddlewaretoken: Cookies.get('csrftoken'),
          text: plainText || ""
        }, function (data) {
          preview.innerHTML = data;
          MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
        }.bind(this));
        return "Loading...";
      }, 1000),
      spellChecker: false
    })
  });
}