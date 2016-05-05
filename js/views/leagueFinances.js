const g = require('../globals');
const ui = require('../ui');
const team = require('../core/team');
const $ = require('jquery');
const ko = require('knockout');
const _ = require('underscore');
const bbgmView = require('../util/bbgmView');
const helpers = require('../util/helpers');
const components = require('./components');


function get(req) {
    return {
        season: helpers.validateSeason(req.params.season)
    };
}

function InitViewModel() {
    this.season = ko.observable();
}

const mapping = {
    teams: {
        create: options => options.data
    }
};

function updateLeagueFinances(inputs, updateEvents, vm) {
    if (updateEvents.indexOf("dbChange") >= 0 || updateEvents.indexOf("firstRun") >= 0 || inputs.season !== vm.season() || inputs.season === g.season) {
        return team.filter({
            attrs: ["tid", "abbrev", "region", "name"],
            seasonAttrs: ["att", "revenue", "profit", "cash", "payroll", "salaryPaid"],
            season: inputs.season
        }).then(function (teams) {
            return {
                season: inputs.season,
                salaryCap: g.salaryCap / 1000,
                minPayroll: g.minPayroll / 1000,
                luxuryPayroll: g.luxuryPayroll / 1000,
                luxuryTax: g.luxuryTax,
                teams: teams
            };
        });
    }
}

function uiFirst(vm) {
    ko.computed(function () {
        ui.title("League Finances - " + vm.season());
    }).extend({throttle: 1});

    ko.computed(function () {
        var season;
        season = vm.season();
        ui.datatableSinglePage($("#league-finances"), 5, _.map(vm.teams(), function (t) {
            var payroll;
            payroll = season === g.season ? t.payroll : t.salaryPaid;  // Display the current actual payroll for this season, or the salary actually paid out for prior seasons
            return ['<a href="' + helpers.leagueUrl(["team_finances", t.abbrev]) + '">' + t.region + ' ' + t.name + '</a>', helpers.numberWithCommas(helpers.round(t.att)), helpers.formatCurrency(t.revenue, "M"), helpers.formatCurrency(t.profit, "M"), helpers.formatCurrency(t.cash, "M"), helpers.formatCurrency(payroll, "M")];
        }));
    }).extend({throttle: 1});

    ui.tableClickableRows($("#league-finances"));
}

function uiEvery(updateEvents, vm) {
    components.dropdown("league-finances-dropdown", ["seasons"], [vm.season()], updateEvents);
}

module.exports = bbgmView.init({
    id: "leagueFinances",
    get,
    InitViewModel,
    mapping,
    runBefore: [updateLeagueFinances],
    uiFirst,
    uiEvery
});
