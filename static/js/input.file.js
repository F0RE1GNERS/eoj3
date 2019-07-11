$.fn.inputFile = function(data) {
  var sizeLimit = -1;
  if (data !== undefined && data.hasOwnProperty("sizeLimit")) {
    sizeLimit = parseInt(data["sizeLimit"]);
  }
  function changeFunction(e) {
    var file = $(e.target);
    var name = '';
    var size = 0;
    for (var i = 0; i < e.target.files.length; i++) {
      name += e.target.files[i].name + (i + 1 == e.target.files.length ? '' : ', ');
      size += e.target.files[i].size / 1048576;
    }
    $('input:text', file.parent()).val(name);
    if (sizeLimit > 0 && size > sizeLimit) {
      window.alert("File too large! If you insist on uploading, it is likely to fail...");
    }
  }
  if (!this.prop("init")) {
    this.prop("init", true);
    this.find('input:text, .ui.button:not([type="submit"])')
      .on('click', function (e) {
        $(e.target).parent().find('input:file').click();
      })
    ;
    this.on('change', changeFunction);
    this.find('.ui.file.input').on('change', changeFunction);
  }
};
