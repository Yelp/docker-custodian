# Changelog

## [v0.7.4](https://github.com/yelp/docker-custodian/tree/v0.7.4) (2021-06-23)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/v0.7.3...v0.7.4)

**Closed issues:**

- Upgrade requests to version 2.20.0 or later \(CVE-2018-18074\) [\#50](https://github.com/Yelp/docker-custodian/issues/50)
- --dangling-volumes runs into an error when there are no dangling volumes [\#41](https://github.com/Yelp/docker-custodian/issues/41)
- Use kwargs\_from\_env\(\) to get Client kwargs [\#13](https://github.com/Yelp/docker-custodian/issues/13)

**Merged pull requests:**

- Move to GitHub Actions [\#61](https://github.com/Yelp/docker-custodian/pull/61) ([IamTheFij](https://github.com/IamTheFij))
- Remove pre-commit autoupdate in tox [\#60](https://github.com/Yelp/docker-custodian/pull/60) ([IamTheFij](https://github.com/IamTheFij))
- Enable multi-arch builds [\#59](https://github.com/Yelp/docker-custodian/pull/59) ([ViViDboarder](https://github.com/ViViDboarder))
- Simplify instructions for installing with pip [\#54](https://github.com/Yelp/docker-custodian/pull/54) ([dmerejkowsky](https://github.com/dmerejkowsky))
- Bump urllib and requests [\#52](https://github.com/Yelp/docker-custodian/pull/52) ([keymone](https://github.com/keymone))

## [v0.7.3](https://github.com/yelp/docker-custodian/tree/v0.7.3) (2019-04-25)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/v0.7.2...v0.7.3)

**Merged pull requests:**

- Fix null labels [\#51](https://github.com/Yelp/docker-custodian/pull/51) ([mattmb](https://github.com/mattmb))
- adding .secrets.baseline [\#49](https://github.com/Yelp/docker-custodian/pull/49) ([domanchi](https://github.com/domanchi))
- Ignore CHANGELOG.md for the end-of-file precommit hook [\#48](https://github.com/Yelp/docker-custodian/pull/48) ([ATRAN2](https://github.com/ATRAN2))

## [v0.7.2](https://github.com/yelp/docker-custodian/tree/v0.7.2) (2018-03-21)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/v0.7.1...v0.7.2)

## [v0.7.1](https://github.com/yelp/docker-custodian/tree/v0.7.1) (2018-03-21)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/v0.6.1...v0.7.1)

**Implemented enhancements:**

- Remove volumes when removing containers [\#36](https://github.com/Yelp/docker-custodian/pull/36) ([pauloconnor](https://github.com/pauloconnor))
- Add patterns support for exclude-image-file [\#35](https://github.com/Yelp/docker-custodian/pull/35) ([vshlapakov](https://github.com/vshlapakov))

**Fixed bugs:**

- Fix broken filtering for images used by containers [\#43](https://github.com/Yelp/docker-custodian/pull/43) ([chekunkov](https://github.com/chekunkov))

**Closed issues:**

- docker-custodian crashing when cleaning up. [\#38](https://github.com/Yelp/docker-custodian/issues/38)
- backports.ssl-match-hostname\>=3.5 error when running in Docker [\#37](https://github.com/Yelp/docker-custodian/issues/37)
- Publish on PyPI? [\#10](https://github.com/Yelp/docker-custodian/issues/10)

**Merged pull requests:**

- Add --exclude-container-label argument to dcgc [\#47](https://github.com/Yelp/docker-custodian/pull/47) ([ATRAN2](https://github.com/ATRAN2))
- Port to docker lib [\#46](https://github.com/Yelp/docker-custodian/pull/46) ([samiam](https://github.com/samiam))
- Correctly handle empty dangling volumes [\#45](https://github.com/Yelp/docker-custodian/pull/45) ([samiam](https://github.com/samiam))
- Remove dangling volumes [\#40](https://github.com/Yelp/docker-custodian/pull/40) ([ymilki](https://github.com/ymilki))
- Revert docker-py version change [\#39](https://github.com/Yelp/docker-custodian/pull/39) ([pauloconnor](https://github.com/pauloconnor))

## [v0.6.1](https://github.com/yelp/docker-custodian/tree/v0.6.1) (2016-08-31)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/v0.5.1...v0.6.1)

**Closed issues:**

- Add ability to kill/delete running containers by age [\#25](https://github.com/Yelp/docker-custodian/issues/25)
- Add tag to yelp/docker-custodian on the docker hub [\#21](https://github.com/Yelp/docker-custodian/issues/21)
- Error while fetching server API version [\#20](https://github.com/Yelp/docker-custodian/issues/20)
- Could It also clear mesos tmp files? [\#19](https://github.com/Yelp/docker-custodian/issues/19)

**Merged pull requests:**

- Bump to python \>=2.7 [\#33](https://github.com/Yelp/docker-custodian/pull/33) ([danielhoherd](https://github.com/danielhoherd))
- Overriding tox with /bin/true [\#32](https://github.com/Yelp/docker-custodian/pull/32) ([danielhoherd](https://github.com/danielhoherd))
- Bump debian version to 0.6.0 [\#31](https://github.com/Yelp/docker-custodian/pull/31) ([danielhoherd](https://github.com/danielhoherd))
- Remove py26 support, code cleanup [\#27](https://github.com/Yelp/docker-custodian/pull/27) ([kentwills](https://github.com/kentwills))
- Don't remove recently created containers that were never used [\#23](https://github.com/Yelp/docker-custodian/pull/23) ([analogue](https://github.com/analogue))
- Upgrade requirements to fix \#17 [\#18](https://github.com/Yelp/docker-custodian/pull/18) ([dnephin](https://github.com/dnephin))

## [v0.5.1](https://github.com/yelp/docker-custodian/tree/v0.5.1) (2015-09-29)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/v0.4.0...v0.5.1)

**Implemented enhancements:**

- Use Client\(version='auto'\) [\#7](https://github.com/Yelp/docker-custodian/issues/7)

**Fixed bugs:**

- Automatically determining API version doesn't work? [\#17](https://github.com/Yelp/docker-custodian/issues/17)

**Closed issues:**

- Put on the docker hub using the yelp namespace [\#16](https://github.com/Yelp/docker-custodian/issues/16)
- Is it production ready? [\#15](https://github.com/Yelp/docker-custodian/issues/15)

**Merged pull requests:**

- Automatically determine the Docker API version to use [\#12](https://github.com/Yelp/docker-custodian/pull/12) ([jschrantz](https://github.com/jschrantz))
- Add install instructions to the README [\#9](https://github.com/Yelp/docker-custodian/pull/9) ([dnephin](https://github.com/dnephin))
- Fix readme formatting [\#8](https://github.com/Yelp/docker-custodian/pull/8) ([dnephin](https://github.com/dnephin))
- Support excluding some images from removal [\#6](https://github.com/Yelp/docker-custodian/pull/6) ([dnephin](https://github.com/dnephin))
- Add .travis.yml [\#5](https://github.com/Yelp/docker-custodian/pull/5) ([dnephin](https://github.com/dnephin))

## [v0.4.0](https://github.com/yelp/docker-custodian/tree/v0.4.0) (2015-07-08)

[Full Changelog](https://github.com/yelp/docker-custodian/compare/d7d25053e09b7006d16125dd3b967b845c599eaf...v0.4.0)



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
