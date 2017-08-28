$.fn.simpleMDE = function () {
  $(this).each(function () {
    new SimpleMDE({
      element: this,
      forceSync: true,
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
    });
  });
};

$("textarea.markdown").simpleMDE();
