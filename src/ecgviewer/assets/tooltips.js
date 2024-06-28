window.dccFunctions = window.dccFunctions || {};

const twoDigits = new Intl.NumberFormat(undefined,
    {
        minimumIntegerDigits: 2,
        roundingIncrement: 1,
        useGrouping: false
    });

window.dccFunctions.secs_to_timestamp = function (fs) {
    let m = Math.floor(fs / 60 + 0.1);
    let s = Math.floor(fs % 60 + 0.1);
    let ms = Math.floor((fs * 100 + 0.1) % 100);
    return `${twoDigits.format(m)}:${twoDigits.format(s)}:${twoDigits.format(ms)}`;
}
