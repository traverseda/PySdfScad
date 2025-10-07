{
  description = "Python Qt development environment with UV";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python and UV
            python311
            uv

            # Qt libraries
            #qt6.full
            qt6.qtbase
            #qt6.qttools

            # Python Qt bindings (available system-wide for reference)
            python311Packages.pyqt6
            python311Packages.pyside6

            # Development tools
            python311Packages.pip
          ];

          shellHook = ''
            echo "Qt Python development environment with UV"
            echo "Python: $(python --version)"
            echo "UV: $(uv --version)"
            echo ""
            echo "Use 'uv init' to create a new project"
            echo "Use 'uv add pyqt6' or 'uv add pyside6' to add Qt bindings"
            echo "Use 'uv run python your_app.py' to run your application"
          '';

          # Required for Qt applications
          QT_QPA_PLATFORM_PLUGIN_PATH = "${pkgs.qt6.qtbase}/lib/qt-6/plugins";
          LD_LIBRARY_PATH = "${pkgs.lib.makeLibraryPath [ pkgs.qt6.qtbase ]}";
        };
      }
    );
}
