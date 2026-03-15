class Oure < Formula
  desc "Orbital Uncertainty & Risk Engine for Satellite Conjunction Analysis"
  homepage "https://github.com/h-rishi16/oure"
  url "https://github.com/h-rishi16/oure/archive/refs/tags/v1.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256" # I will show you how to get this
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/oure", "--version"
  end
end
