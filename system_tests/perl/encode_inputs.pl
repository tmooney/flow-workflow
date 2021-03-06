#!/usr/bin/env perl

use Flow;
use JSON;
use File::Slurp qw/read_file/;

use strict;
use warnings;

die "Give input/output files!!" unless @ARGV == 2;
my ($in, $out) = @ARGV;

my $json = new JSON->allow_nonref;
my $in_txt = read_file($in) || die "Failed to decode from $in";
my $hash = $json->decode($in_txt) || die "Failed to encode json";
Flow::write_outputs($out, $hash) || die "Failed to write outputs to $out";
