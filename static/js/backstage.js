$(".ui.progress").each(function () {
  if ($(this).data("progress")) {
    $(this).show();
    $(this).progress({
      percent: $(this).data("progress")
    });
  }
});