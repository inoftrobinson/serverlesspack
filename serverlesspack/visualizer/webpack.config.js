const isProduction = process.env.NODE_ENV === 'production';

const webpack = require("webpack");
const path = require('path');
const SpeedMeasurePlugin = require("speed-measure-webpack-plugin");

const WebpackManifestPlugin = require('webpack-manifest-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');

const smp = new SpeedMeasurePlugin();
module.exports = smp.wrap({
	mode: isProduction ? 'production' : 'development',
	devtool: 'inline-source-map',
	entry: {
        'app': path.join(__dirname, './NetworkDirectedGraphComponent.tsx')
    },
	output: {
		path: path.join(__dirname, `/dist/${isProduction ? 'prod': 'dev'}`),
		filename: '[name]_bundle.js',
		publicPath: `/dist/${isProduction ? 'prod': 'dev'}/`
	},
    resolve: {
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.html', '.scss'],
    },
    optimization: {
        concatenateModules: true, providedExports: false, usedExports: false,
        minimize: isProduction,
        minimizer: [
            new TerserPlugin({
                parallel: true,
                terserOptions: {
                    ecma: 6
                }
            }),
            new CssMinimizerPlugin()
        ]
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: '[name].css',
            chunkFilename: '[id].css'
        }),
    ],
    module: {
        rules: [
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader']
            },
            {
                test: /\.(js|tsx?)$/,
                loader: 'babel-loader',
                exclude: /node_modules/,
            },
            {
                test: /\.(js|tsx?)$/,
                loader: 'ts-loader',
                options: {
                    transpileOnly: true
                }
            },
            {
                test: /\.html$/i,
                loader: 'html-loader'
            },
            {
                test: /\.(png|jp(e*)g|svg)$/,
                use: [{
                    loader: 'url-loader',
                    options: {
                        limit: 8000, // Convert images < 8kb to base64 strings
                        name: 'images/[hash]-[name].[ext]'
                    }
                }]
            },
            {
                test: /\.(ttf|eot|svg)$/,
                use: {
                    loader: 'file-loader',
                    options: {
                        name: 'fonts/[hash].[ext]'
                    }
                }
            },
            {
                test: /\.scss$/,
                use: ['style-loader', 'css-loader', 'sass-loader'],
                include: path.resolve(__dirname, '../'),
            },
        ]
    }
});
