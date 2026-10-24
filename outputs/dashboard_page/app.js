// start-up: open the tab named in the link, then redraw the open tab on every data or width change
const Z = window.ZS;
const TABS = ['today', 'fixtures', 'season', 'deep', 'accuracy'];
const wanted = location.hash.slice(1);
let first = true;
let pendingScroll = wanted && !TABS.includes(wanted) ? wanted : '';

dash.onData(() => {
  Z.fillMarks(document.getElementById('top'));
  if (first) {
    first = false;
    if (TABS.includes(wanted) && wanted !== 'today') { Z.show(wanted); return; }
  }
  Z.redraw();
  if (pendingScroll && dash.data('fixtures').status === 'ok') {
    const target = document.getElementById(pendingScroll);
    pendingScroll = '';
    if (target && !target.closest('template')) target.scrollIntoView();
  }
});
