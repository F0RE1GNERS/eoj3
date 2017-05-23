var map = {
  'python': 'python',
  'java': 'java',
  'cpp': 'c_cpp',
  'c': 'c_cpp'
};
var editor = ace.edit("editor");
var lang = $("#id_lang");
var code = $("#id_code");
editor.getSession().setValue(code.val());
editor.setTheme("ace/theme/chrome");
editor.getSession().setMode("ace/mode/" + map[lang.val()]);
lang.on("change", function (event) {
  editor.getSession().setMode("ace/mode/" + map[event.target.value]);
});
function setVal() {
  code.val(editor.getSession().getValue())
}
$('form').submit(function () {
  $(this).find('button[type=submit]').prop('disabled', true);
});